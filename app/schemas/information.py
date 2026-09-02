from pydantic import BaseModel
from typing import List, Optional, Any


class InformationItem(BaseModel):
    type: str
    title: str
    summary: str
    fields: dict


class ExtractionResponse(BaseModel):
    information: List[InformationItem]