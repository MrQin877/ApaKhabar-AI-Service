import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app.core.config import Settings
from app.schemas.news import NewsRequest, NewsArticle
from app.services.document_service import DocumentService
from app.services.extraction_service import extract_document
from app.services.editorial_brief import build_brief, coverage_issues, natural_dates, deduplicate_narrative
from app.services.agent_service import AgentService
from test_agent_workflow import ScriptedModel

FIXTURE = Path(__file__).resolve().parents[1] / 'sample_data/health_screening_test.csv'


def health_information():
    return extract_document(DocumentService.normalize(FIXTURE.read_bytes(), FIXTURE.name, 'text/csv'))


class TableNewsTests(unittest.TestCase):
    def test_health_csv_totals_are_from_all_rows(self):
        with patch('app.services.extraction_service.AIService.extract_information') as model:
            result = health_information()
        model.assert_not_called()
        analysis = result.information[0].fields['table_analysis']
        self.assertEqual(analysis['record_count'], 120)
        self.assertEqual(analysis['record_unit'], 'kunjungan')
        self.assertIsNone(analysis['unique_person_count'])
        self.assertEqual(analysis['columns']['jenis_layanan']['counts'], {
            'Pemeriksaan tekanan darah': 40, 'Pemeriksaan gula darah': 40, 'Konsultasi kesehatan umum': 40})
        self.assertEqual(analysis['columns']['hasil_skrining']['counts']['Perlu pemeriksaan ulang'], 16)
        self.assertEqual(analysis['columns']['hasil_skrining']['counts']['Perlu pemeriksaan lanjutan'], 8)
        self.assertEqual(analysis['columns']['tindak_lanjut']['counts']['Disarankan pemeriksaan ulang'], 24)
        self.assertEqual(analysis['columns']['tindak_lanjut']['counts']['Disarankan konsultasi lanjutan ke Puskesmas'], 12)
        self.assertEqual(analysis['source_row_ranges'], [[2, 121]])

    def test_health_csv_draft_revises_repetition_and_missing_totals(self):
        # The test model deliberately returns a flawed first draft. Revision text is
        # built from the actual brief, not a canned health-specific expected answer.
        class BriefWriter(ScriptedModel):
            writes = 0
            def structured(self, schema, system, data, *args):
                if schema is not NewsArticle:
                    return super().structured(schema, system, data, *args)
                self.writes += 1
                payload = json.loads(data)
                brief = payload['editorial_brief']
                result = super().structured(schema, system, data, *args)
                result.lead = 'Data uji mencatat kegiatan pada 2026-09-21 di Balai Desa Punggul.'
                if self.writes == 1:
                    result.body = ['Kegiatan berlangsung pada 2026-09-21 di Balai Desa Punggul.']
                else:
                    assert payload['review']['editorial_issues']
                    result.body = [f"{f['label']}: {f['count']} {f['unit']}." for f in brief['required_totals']]
                    result.body.append('Jumlah kunjungan tidak menunjukkan jumlah orang unik.')
                return result
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(_env_file=None, agent_db_path=str(Path(directory) / 'graph.sqlite'))
            model = BriefWriter()
            result = AgentService(settings, model).run(NewsRequest(information=health_information()))
        text = ' '.join([result.article.lead, *result.article.body])
        self.assertEqual(model.writes, 2)
        self.assertEqual(text.count('21 September 2026'), 1)
        self.assertEqual(text.count('Balai Desa Punggul'), 1)
        self.assertNotIn('2026-09-21', text)
        for label, count in [('Jumlah kunjungan', 120), ('Pemeriksaan tekanan darah', 40),
                             ('Pemeriksaan gula darah', 40), ('Konsultasi kesehatan umum', 40),
                             ('Perlu pemeriksaan ulang', 16), ('Perlu pemeriksaan lanjutan', 8),
                             ('Disarankan pemeriksaan ulang', 24), ('Disarankan konsultasi lanjutan ke Puskesmas', 12)]:
            self.assertIn(f'{label}: {count} kunjungan', text)
        self.assertEqual(result.quality['editorial_issues'], [])
        self.assertEqual(result.status, 'completed')  # Still a moderator draft, never published.

    def test_other_topics_and_later_events_are_not_sampled_away(self):
        data = 'event_name,quantity,product\n' + 'Food drive,2,Rice\n' * 35 + 'Workshop,3,Books\n'
        result = extract_document(DocumentService.normalize(data.encode(), 'other.csv', 'text/csv'))
        self.assertEqual(len(result.information), 2)
        self.assertEqual(result.information[0].fields['table_analysis']['columns']['quantity']['sum'], '70')
        self.assertEqual(result.information[1].fields['table_analysis']['record_count'], 1)

    def test_dates_invalid_dates_and_unique_people(self):
        self.assertEqual(natural_dates('2026-01-02; 2026-02-30'), '2 Januari 2026; 2026-02-30')
        brief = build_brief({'x': health_information().information[0].model_dump()})
        issues = coverage_issues({'lead': 'Ada 120 orang.', 'body': ['Kegiatan selesai.'], 'sources_used': ['x']}, brief)
        self.assertTrue(any('Unsupported unique-person' in issue for issue in issues))

    def test_repetition_cleanup_preserves_new_results_and_negation(self):
        brief = build_brief({'x': health_information().information[0].model_dump()})
        article = SimpleNamespace(
            lead='Kegiatan mencatat 120 kunjungan di Balai Desa Punggul pada 21 September 2026.',
            body=['Kegiatan berlangsung di Balai Desa Punggul pada 21 September 2026.',
                  'Dari total 120 kunjungan tersebut, 16 memerlukan pemeriksaan ulang.',
                  'Di Balai Desa Punggul, 8 memerlukan pemeriksaan lanjutan.',
                  'Kegiatan tidak mencatat 120 kunjungan.'])
        cleaned = deduplicate_narrative(article, brief)
        self.assertEqual(cleaned.body, [
            '16 memerlukan pemeriksaan ulang.',
            'Di Balai Desa Punggul, 8 memerlukan pemeriksaan lanjutan.',
            'Kegiatan tidak mencatat 120 kunjungan.'])

    def test_csv_cells_with_pipes_and_missing_values(self):
        result = extract_document(DocumentService.normalize(b'product,quantity\n"A | B",2\nC,\n', 'quoted.csv', 'text/csv'))
        columns = result.information[0].fields['table_analysis']['columns']
        self.assertEqual(columns['product']['counts']['A | B'], 1)
        self.assertEqual(columns['quantity']['missing'], 1)

    def test_targeted_news_keeps_full_statistics(self):
        document = DocumentService.normalize(FIXTURE.read_bytes(), 'health.csv', 'text/csv')
        with patch('app.services.extraction_service.AIService._structured_chat', return_value={
            'summary_indexes': [0], 'needs_row_details': False}), patch(
                'app.services.extraction_service.AIService.extract_information') as raw:
            result = extract_document(document, 'Buat berita kegiatan dan hasilnya')
        raw.assert_not_called()
        self.assertEqual(result.information[0].fields['table_analysis']['record_count'], 120)

    def test_excel_and_semicolon_csv_share_statistics(self):
        from openpyxl import Workbook
        workbook = Workbook()
        workbook.active.append(['product', 'quantity'])
        workbook.active.append(['Rice', 4])
        workbook.active.append(['Books', 7])
        data = io.BytesIO()
        workbook.save(data)
        for content, filename in [(data.getvalue(), 'supplies.xlsx'), (b'product;quantity\nRice;4\nBooks;7\n', 'supplies.csv')]:
            result = extract_document(DocumentService.normalize(content, filename, None))
            self.assertEqual(result.information[0].fields['table_analysis']['columns']['quantity']['sum'], '11')

    def test_repeated_visit_ids_do_not_become_distinct_visits(self):
        data = b'visit_id,service\n1,A\n1,B\n2,A\n'
        result = extract_document(DocumentService.normalize(data, 'visits.csv', 'text/csv'))
        stats = result.information[0].fields['table_analysis']
        self.assertEqual(stats['record_count'], 3)
        self.assertEqual(stats['distinct_visit_id_count'], 2)
        self.assertEqual(stats['record_unit'], 'catatan')
        self.assertIsNone(stats['unique_person_count'])

    @unittest.skipUnless(os.getenv('APAKHABAR_LIVE_NEWS_TEST') == '1', 'Opt-in local model integration test')
    def test_live_health_csv_article(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(agent_db_path=str(Path(directory) / 'graph.sqlite'), agent_max_seconds=600)
            result = AgentService(settings).run(NewsRequest(information=health_information(),
                instructions='Buat laporan berita data uji ini. Rangkum kegiatan, layanan, hasil skrining dan tindak lanjut. Pertahankan penanda bahwa data ini fiktif.'))
            self.assertIsNotNone(result.article, result.model_dump())
            text = ' '.join([result.article.lead, *result.article.body])
            self.assertIn('120', text)
            for count in ('40', '16', '8', '24', '12'):
                self.assertRegex(text, rf'\b{count}\b')
            self.assertEqual(text.count('21 September 2026'), 1)
            self.assertEqual(text.casefold().count('balai desa punggul'), 1)
            self.assertNotRegex(text.casefold(), r'120\s+(orang|warga|peserta)')
            self.assertFalse(result.quality['editorial_issues'], result.quality)
            print(json.dumps(result.article.model_dump(), ensure_ascii=False, indent=2))
