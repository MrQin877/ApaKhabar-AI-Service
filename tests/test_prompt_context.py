import copy
import json
import unittest
from app.services.prompt_context import compact_context


class PromptContextTests(unittest.TestCase):
    def test_duplicate_sources_referenced_and_input_unchanged(self):
        source = {'content': 'Historical evidence ' * 1000, 'context_type': 'historical_background'}
        data = {'sources': {'history:1': source}, 'editorial_brief': {
            'supporting_facts': [{'source_id': 'history:1', 'facts': source}],
            'required_totals': [{'count': 64, 'unit': 'catatan'}]}}
        original = copy.deepcopy(data)
        result = compact_context(data)
        self.assertEqual(data, original)
        self.assertEqual(result['sources'], data['sources'])
        self.assertEqual(result['editorial_brief']['required_totals'], data['editorial_brief']['required_totals'])
        self.assertNotIn('facts', result['editorial_brief']['supporting_facts'][0])
        self.assertLess(len(json.dumps(result)), len(json.dumps(data)) * .6)

    def test_statistics_and_provenance_preserved(self):
        stats = {'record_count': 64, 'unique_person_count': None, 'limitations': ['No participant ID']}
        quote = 'Perhitungan seluruh baris sumber: ' + json.dumps(stats)
        source = {'fields': {'table_analysis': stats}, 'evidence': [
            {'source': 'file.csv', 'quote': quote}, {'source': 'file.csv', 'quote': 'Other evidence'}]}
        result = compact_context({'sources': {'x': source}})['sources']['x']
        self.assertEqual(result['fields']['table_analysis'], stats)
        self.assertEqual(result['evidence'][0]['source'], 'file.csv')
        self.assertEqual(result['evidence'][1]['quote'], 'Other evidence')
        source['evidence'][0]['quote'] = 'Perhitungan seluruh baris sumber: {"record_count":50}'
        self.assertEqual(compact_context({'sources': {'x': source}})['sources']['x'], source)
