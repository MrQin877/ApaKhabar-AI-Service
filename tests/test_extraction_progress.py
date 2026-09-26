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
