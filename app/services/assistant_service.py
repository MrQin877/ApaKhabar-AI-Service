import re

from app.schemas.assistant import AssistantIntentRequest, AssistantIntentResponse


class AssistantIntentService:
    """Deterministic first-pass routing for the unified assistant workspace."""

    _general_extract = re.compile(
        r"\b(extract|ekstrak|analyse|analyze|analisis)\b.*\b(all|everything|"
        r"semua|seluruh|important|penting)\b|\b(don'?t know|tidak tahu|gak tahu|"
        r"tak tahu)\b.*\b(file|document|dokumen|inside|isinya?)\b",
        re.IGNORECASE,
    )
    _extract = re.compile(
        r"\b(extract|ekstrak|ambil informasi|cari dalam (file|dokumen)|"
        r"informasi dari (file|dokumen))\b",
        re.IGNORECASE,
    )
    _generate = re.compile(
        r"\b(generate|create|write|buat|bikin|tulis)\b.{0,30}\b(news|article|"
        r"berita|artikel|laporan)\b",
        re.IGNORECASE,
    )
    _revise = re.compile(
        r"\b(revise|rewrite|edit|change|shorten|shorter|summarize|formalize|ubah|"
        r"perbaiki|ringkas|pendekkan|lebih formal|ganti judul)\b",
        re.IGNORECASE,
    )
    _search = re.compile(
        r"\b(search|find|recommend|related|cari|temukan|rekomendasi|terkait)\b",
        re.IGNORECASE,
    )
    _noise = re.compile(
        r"^(hi|hello|hey|hai|halo|test|abc|\?+|\.+|,+|ok|okay)\W*$",
        re.IGNORECASE,
    )

    @classmethod
    def classify(cls, request: AssistantIntentRequest) -> AssistantIntentResponse:
        message = " ".join(request.message.split())

        if request.has_draft and cls._revise.search(message):
            return AssistantIntentResponse(
                intent="revise_news",
                normalized_query=message,
                confidence=0.98,
            )
        if cls._generate.search(message):
            return AssistantIntentResponse(
                intent="generate_news",
                normalized_query=message,
                confidence=0.98,
            )
        if cls._general_extract.search(message):
            return AssistantIntentResponse(
                intent="extract_information",
                extraction_mode="general",
                normalized_query="Extract all distinct and important information.",
                confidence=0.98,
            )
        if cls._extract.search(message):
            return AssistantIntentResponse(
                intent="extract_information",
                extraction_mode="targeted",
                normalized_query=message,
                confidence=0.92,
            )
        if cls._search.search(message):
            return AssistantIntentResponse(
                intent="search_information",
                normalized_query=message,
                confidence=0.90,
            )
        if request.has_files and cls._noise.match(message):
            return AssistantIntentResponse(
                intent="conversation",
                confidence=0.99,
                guidance=(
                    "File telah diterima. Pilih apakah Anda ingin mengekstrak semua "
                    "informasi penting atau menentukan informasi tertentu."
                ),
            )
        return AssistantIntentResponse(
            intent="conversation",
            confidence=0.65,
            guidance="Jelaskan apakah Anda ingin mengekstrak informasi, mencari sumber, atau membuat berita.",
        )
