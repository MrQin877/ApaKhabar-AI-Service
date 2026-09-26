from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.information import ExtractionResponse


ElementType = Literal["paragraph", "table_row"]


class SourceReference(BaseModel):
    filename: str
    page: int | None = None
    sheet: str | None = None
    row: int | None = None
    paragraph: int | None = None


class DocumentElement(BaseModel):
    element_type: ElementType
    content: str
    source: SourceReference
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedDocument(BaseModel):
    document_id: str
    filename: str
    media_type: str
    character_count: int
    elements: list[DocumentElement]

    def as_model_text(self) -> str:
        lines: list[str] = []
        for element in self.elements:
            source = element.source
            location = [f"filename={source.filename}"]
            if source.page is not None:
                location.append(f"page={source.page}")
            if source.sheet is not None:
                location.append(f"sheet={source.sheet}")
            if source.row is not None:
                location.append(f"row={source.row}")
            if source.paragraph is not None:
                location.append(f"paragraph={source.paragraph}")
            marker = ", ".join(location) or "document"
            lines.append(f"[source: {marker}] {element.content}")
        return "\n".join(lines)


class DocumentExtractionResponse(BaseModel):
    document: NormalizedDocument
    extraction: ExtractionResponse
