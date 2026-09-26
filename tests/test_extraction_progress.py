import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.core.config import Settings
from app.services import extraction_progress
from app.services.document_service import DocumentService
from app.services.extraction_service import extract_document


class ExtractionProgressTests(unittest.TestCase):
    def test_chunk_progress_is_durable_and_available_during_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(_env_file=None, agent_db_path=str(Path(directory) / 'agent'))
            document = DocumentService.normalize(data=('A factual sentence. ' * 900).encode(), filename='long.txt', media_type='text/plain')
            observed = []
            def extract(*args):
                observed.append(extraction_progress.inspect('test'))
                return {'information': []}
            with patch('app.services.extraction_progress.get_settings', return_value=settings), patch(
                'app.services.extraction_service.AIService.extract_information', side_effect=extract
            ):
                result = extract_document(document, progress=lambda *args, **kwargs: extraction_progress.record('test', *args, **kwargs))
                self.assertEqual(result.information, [])
                self.assertGreater(len(observed), 1)
                self.assertEqual([p['completed_chunks'] for p in observed], list(range(len(observed))))
                self.assertTrue(all(p['stage'] == 'extracting' for p in observed))
                final = extraction_progress.inspect('test')
                self.assertEqual(final['stage'], 'completed')
                self.assertEqual(final['completed_chunks'], final['total_chunks'])
                with self.assertRaises(KeyError):
                    extraction_progress.inspect('other-id')

    def test_large_table_is_summarized_with_count_and_samples(self):
        from app.schemas.document import NormalizedDocument, DocumentElement, SourceReference
        for sheet in (None, 'Attendance'):
            elements = [DocumentElement(element_type='table_row', content='event_id | event_name | attendee_name',
                source=SourceReference(filename='attendance', sheet=sheet, row=1))]
            elements += [DocumentElement(element_type='table_row', content='1 | Workshop | ' + f'Person {i}',
                source=SourceReference(filename='attendance', sheet=sheet, row=i)) for i in range(2, 102)]
            document = NormalizedDocument(document_id='test', filename='attendance', media_type='text/csv', character_count=22000, elements=elements)
            with patch('app.services.extraction_service.AIService.extract_information', return_value={'information': []}) as model:
                extract_document(document)
            # Large table should be summarized into a single compact chunk
            self.assertEqual(model.call_count, 1)
            chunk_text = model.call_args_list[0].args[0]
            # Header row is preserved
            self.assertIn('event_id | event_name | attendee_name', chunk_text)
            # Pre-computed row count is injected
            self.assertIn('section=table-summary]', chunk_text)
            self.assertIn('Total data rows in this table section', chunk_text)
            self.assertIn('100', chunk_text)  # 101 elements - 1 header = 100 data rows
            # Sample rows are included
            self.assertIn('Person 2', chunk_text)
            # Not all rows are sent
            self.assertNotIn('Person 99', chunk_text)

    def test_small_table_is_sent_verbatim(self):
        from app.schemas.document import NormalizedDocument, DocumentElement, SourceReference
        elements = [DocumentElement(element_type='table_row', content='name | amount',
            source=SourceReference(filename='budget.csv', row=1))]
        elements += [DocumentElement(element_type='table_row', content=f'Item {i} | {i * 100}',
            source=SourceReference(filename='budget.csv', row=i)) for i in range(2, 12)]
        document = NormalizedDocument(document_id='test', filename='budget.csv', media_type='text/csv', character_count=500, elements=elements)
        with patch('app.services.extraction_service.AIService.extract_information', return_value={'information': []}) as model:
            extract_document(document)
        chunk_text = model.call_args_list[0].args[0]
        # Small table (10 data rows <= threshold) should NOT be summarized
        self.assertNotIn('section=table-summary]', chunk_text)
        # All rows should be present
        for i in range(2, 12):
            self.assertIn(f'Item {i}', chunk_text)

    def test_model_chunk_schema_bounds_items_not_combined_document(self):
        from app.services.ai_service import ExtractionChunkResponse
        from app.schemas.information import ExtractionResponse
        self.assertEqual(ExtractionChunkResponse.model_json_schema()['properties']['information']['maxItems'], 5)
        self.assertNotIn('maxItems', ExtractionResponse.model_json_schema()['properties']['information'])
