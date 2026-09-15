import io
import unittest

import fitz
from docx import Document
from openpyxl import Workbook

from app.services.document_service import (
    DocumentService,
    EmptyDocumentError,
    UnsupportedDocumentError,
)


class DocumentServiceTests(unittest.TestCase):
    def test_txt_preserves_paragraph_reference(self):
        result = DocumentService.normalize(
            b"First line\nSecond line",
            "notes.txt",
            "text/plain",
        )
        self.assertEqual(len(result.elements), 2)
        self.assertEqual(result.elements[1].source.paragraph, 2)

    def test_csv_preserves_row_reference(self):
        result = DocumentService.normalize(
            b"name,amount\nAid,5000",
            "budget.csv",
            "text/csv",
        )
        self.assertEqual(result.elements[1].source.row, 2)
        self.assertEqual(result.elements[1].content, "Aid | 5000")

    def test_docx_extracts_paragraph(self):
        document = Document()
        document.add_paragraph("Community programme")
        buffer = io.BytesIO()
        document.save(buffer)

        result = DocumentService.normalize(
            buffer.getvalue(),
            "notice.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertEqual(result.elements[0].content, "Community programme")

    def test_xlsx_preserves_sheet_and_row(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Budget"
        sheet.append(["Department", "Amount"])
        sheet.append(["Health", 5000])
        buffer = io.BytesIO()
        workbook.save(buffer)

        result = DocumentService.normalize(
            buffer.getvalue(),
            "budget.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertEqual(result.elements[1].source.sheet, "Budget")
        self.assertEqual(result.elements[1].source.row, 2)

    def test_pdf_preserves_page_reference(self):
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), "Verified announcement")
        data = document.tobytes()
        document.close()

        result = DocumentService.normalize(
            data,
            "announcement.pdf",
            "application/pdf",
        )
        self.assertEqual(result.elements[0].source.page, 1)

    def test_rejects_unsupported_extension(self):
        with self.assertRaises(UnsupportedDocumentError):
            DocumentService.normalize(b"content", "archive.zip", "application/zip")

    def test_rejects_empty_document(self):
        with self.assertRaises(EmptyDocumentError):
            DocumentService.normalize(b"\n\n", "empty.txt", "text/plain")

if __name__ == "__main__":
    unittest.main()
