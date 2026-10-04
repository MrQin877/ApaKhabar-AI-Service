import csv
import io
import uuid
from pathlib import Path

import fitz
from app.services.poster_ocr import regional_ocr
from docx import Document
from openpyxl import load_workbook

from app.core.config import get_settings

from app.schemas.document import (
    DocumentElement,
    NormalizedDocument,
    SourceReference,
)


class UnsupportedDocumentError(ValueError):
    """Raised when an uploaded file type is not supported."""


class EmptyDocumentError(ValueError):
    """Raised when no usable content can be extracted."""


class DocumentService:
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xlsm", ".csv", ".txt", ".jpg", ".jpeg", ".png"}

    @classmethod
    def normalize(
        cls,
        data: bytes,
        filename: str,
        media_type: str | None,
    ) -> NormalizedDocument:
        safe_name = Path(filename).name
        extension = Path(safe_name).suffix.lower()
        if extension not in cls.SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(cls.SUPPORTED_EXTENSIONS))
            raise UnsupportedDocumentError(
                f"Unsupported file type. Supported types: {supported}."
            )

        extractors = {
            ".pdf": cls._pdf_elements,
            ".docx": cls._docx_elements,
            ".xlsx": cls._xlsx_elements,
            ".xlsm": cls._xlsx_elements,
            ".jpg": cls._image_elements,
            ".jpeg": cls._image_elements,
            ".png": cls._image_elements,
            ".csv": cls._csv_elements,
            ".txt": cls._text_elements,
        }
        elements = extractors[extension](data, safe_name)
        if not elements:
            raise EmptyDocumentError(
                "No readable text or table data was found in the document."
            )

        return NormalizedDocument(
            document_id=str(uuid.uuid4()),
            filename=safe_name,
            media_type=media_type or "application/octet-stream",
            character_count=sum(len(item.content) for item in elements),
            elements=elements,
        )

    @staticmethod
    def _pdf_elements(data: bytes, filename: str) -> list[DocumentElement]:
        elements: list[DocumentElement] = []
        try:
            with fitz.open(stream=data, filetype="pdf") as document:
                if len(document) > get_settings().ocr_max_pages:
                    raise UnsupportedDocumentError("Document exceeds configured page limit")
                for page_number, page in enumerate(document, start=1):
                    blocks = page.get_text("blocks")
                    if not any(str(block[4]).strip() for block in blocks):
                        regions = regional_ocr(page, get_settings().ocr_language)
                        if regions:
                            for text, region in regions:
                                elements.append(DocumentElement(element_type="paragraph", content=text,
                                    source=SourceReference(filename=filename, page=page_number),
                                    metadata={"ocr_method": "regional_tesseract", "region": region, "requires_visual_review": True}))
                            continue
                        try:
                            textpage = page.get_textpage_ocr(language=get_settings().ocr_language, dpi=200, full=True)
                            blocks = page.get_text("blocks", textpage=textpage)
                        except RuntimeError as exc:
                            raise UnsupportedDocumentError("OCR unavailable. Install Tesseract and the configured language data.") from exc
                    for block in blocks:
                        text = " ".join(block[4].split())
                        if text:
                            elements.append(
                                DocumentElement(
                                    element_type="paragraph",
                                    content=text,
                                    source=SourceReference(
                                        filename=filename,
                                        page=page_number,
                                    ),
                                )
                            )
        except (fitz.FileDataError, RuntimeError) as exc:
            raise UnsupportedDocumentError("The PDF is invalid or damaged.") from exc
        return elements

    @staticmethod
    def _image_elements(data: bytes, filename: str) -> list[DocumentElement]:
        try:
            with fitz.open(stream=data) as image:
                pdf = image.convert_to_pdf()
            return DocumentService._pdf_elements(pdf, filename)
        except UnsupportedDocumentError:
            raise
        except Exception as exc:
            raise UnsupportedDocumentError("Image is invalid or OCR is unavailable") from exc

    @staticmethod
    def _docx_elements(data: bytes, filename: str) -> list[DocumentElement]:
        try:
            document = Document(io.BytesIO(data))
        except Exception as exc:
            raise UnsupportedDocumentError("The DOCX file is invalid or damaged.") from exc

        elements: list[DocumentElement] = []
        for index, paragraph in enumerate(document.paragraphs, start=1):
            text = " ".join(paragraph.text.split())
            if text:
                elements.append(
                    DocumentElement(
                        element_type="paragraph",
                        content=text,
                        source=SourceReference(
                            filename=filename,
                            paragraph=index,
                        ),
                    )
                )

        for table_index, table in enumerate(document.tables, start=1):
            for row_index, row in enumerate(table.rows, start=1):
                values = [" ".join(cell.text.split()) for cell in row.cells]
                if any(values):
                    elements.append(
                        DocumentElement(
                            element_type="table_row",
                            content=" | ".join(values),
                            source=SourceReference(
                                filename=filename,
                                row=row_index,
                            ),
                            metadata={"table": table_index, "cells": values},
                        )
                    )
        return elements

    @staticmethod
    def _xlsx_elements(data: bytes, filename: str) -> list[DocumentElement]:
        try:
            workbook = load_workbook(
                io.BytesIO(data),
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise UnsupportedDocumentError("The XLSX file is invalid or damaged.") from exc

        elements: list[DocumentElement] = []
        try:
            for worksheet in workbook.worksheets:
                for row_index, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
                    values = ["" if value is None else str(value) for value in row]
                    if any(value.strip() for value in values):
                        elements.append(
                            DocumentElement(
                                element_type="table_row",
                                content=" | ".join(values),
                                source=SourceReference(
                                    filename=filename,
                                    sheet=worksheet.title,
                                    row=row_index,
                                ),
                                metadata={"cells": values},
                            )
                        )
        finally:
            workbook.close()
        return elements

    @staticmethod
    def _csv_elements(data: bytes, filename: str) -> list[DocumentElement]:
        text = DocumentService._decode_text(data)
        elements: list[DocumentElement] = []
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        for row_index, row in enumerate(csv.reader(io.StringIO(text), dialect), start=1):
            values = [value.strip() for value in row]
            if any(values):
                elements.append(
                    DocumentElement(
                        element_type="table_row",
                        content=" | ".join(values),
                        source=SourceReference(filename=filename, row=row_index),
                        metadata={"cells": values},
                    )
                )
        return elements

    @staticmethod
    def _text_elements(data: bytes, filename: str) -> list[DocumentElement]:
        text = DocumentService._decode_text(data)
        elements: list[DocumentElement] = []
        for index, paragraph in enumerate(text.splitlines(), start=1):
            cleaned = " ".join(paragraph.split())
            if cleaned:
                elements.append(
                    DocumentElement(
                        element_type="paragraph",
                        content=cleaned,
                        source=SourceReference(
                            filename=filename,
                            paragraph=index,
                        ),
                    )
                )
        return elements

    @staticmethod
    def _decode_text(data: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "cp1252"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UnsupportedDocumentError("The text encoding is not supported.")
