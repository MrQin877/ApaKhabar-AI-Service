import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import fitz
from app.services.poster_ocr import regional_ocr
from app.services.document_service import DocumentService


class PosterOCRTests(unittest.TestCase):
    def test_confidence_filter_and_bounded_region_calls(self):
        doc = fitz.open()
        page = doc.new_page()
        tsv = ('block_num\tpar_num\tline_num\tconf\ttext\n'
               '1\t1\t1\t95\t25 Oktober 2026\n'
               '1\t1\t2\t12\tgarbled text\n').encode()
        with patch('app.services.poster_ocr.shutil.which', return_value='/bin/tesseract'), patch(
            'app.services.poster_ocr.subprocess.run', return_value=SimpleNamespace(stdout=tsv)) as run:
            result = regional_ocr(page, 'ind+eng')
        self.assertEqual(result, [('25 Oktober 2026', i) for i in range(1, 5)])
        self.assertEqual(run.call_count, 4)
        self.assertEqual(run.call_args.kwargs['timeout'], 15)

    def test_native_pdf_skips_ocr(self):
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((40, 40), 'Original source text')
        with patch('app.services.document_service.regional_ocr') as ocr:
            result = DocumentService.normalize(doc.tobytes(), 'text.pdf', 'application/pdf')
        ocr.assert_not_called()
        self.assertEqual(result.elements[0].content, 'Original source text')

    def test_scan_keeps_page_and_region_provenance(self):
        doc = fitz.open()
        doc.new_page()
        with patch('app.services.document_service.regional_ocr', return_value=[('07.00 WITA', 2)]):
            result = DocumentService.normalize(doc.tobytes(), 'scan.pdf', 'application/pdf')
        self.assertEqual(result.elements[0].source.page, 1)
        self.assertEqual(result.elements[0].metadata['region'], 2)
        self.assertEqual(result.elements[0].content, '07.00 WITA')
