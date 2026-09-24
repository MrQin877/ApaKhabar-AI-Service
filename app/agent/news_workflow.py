from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.schemas.news import (
    CompletenessResult,
    MissingInformation,
    NewsGenerationResponse,
    NewsRequest,
    NewsContentType,
)
from app.schemas.tools import (
    AskUserChoice,
    AskUserChoiceToolCall,
    WebSearchInput,
    WebSearchResult,
)
from app.services.ai_service import AIServiceError, OllamaService
from app.services.web_search_service import WebSearchError, WebSearchService


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "news-creation"


def load_skill_prompt(name: str) -> str:
    """Load a version-controlled runtime prompt from the news skill package."""
    path = SKILL_ROOT / "prompts" / f"{name}.md"
    return path.read_text(encoding="utf-8").strip()


@dataclass(frozen=True)
class NewsCreationWorkflow:
    """Run completeness before generation and stop when human input is needed."""

    @staticmethod
    def run(
        request: NewsRequest,
        progress: Callable[[str, str], None] | None = None,
    ) -> NewsGenerationResponse:
        emit = progress or (lambda _stage, _message: None)
        information = request.information_text()
        query = (request.instructions or "").strip()
        content_type = request.content_type or NewsCreationWorkflow._infer_content_type(
            query
        )
        facts = {fact.field: fact.value for fact in request.user_facts}
        has_evidence = "NO APPROVED FACTUAL EVIDENCE" not in information
        web_sources: list[WebSearchResult] = []
        search_attempted = False

        if WebSearchService.should_search(query, has_evidence):
            search_attempted = True
            emit("searching_sources", "Mencari sumber web terbaru dan relevan…")
            try:
                web_sources = WebSearchService.search(
                    WebSearchService.discovery_input(query)
                )
            except WebSearchError:
                web_sources = []

            approval = facts.get("web_source_approval", "").lower()
            if web_sources and "gunakan" not in approval:
                if "jangan" not in approval and not request.clarification_completed:
                    return NewsCreationWorkflow._source_approval_response(web_sources)
                web_sources = []
            elif web_sources:
                information = NewsCreationWorkflow._append_web_sources(
                    information, web_sources
                )

        if not has_evidence and not web_sources and not NewsCreationWorkflow._has_usable_user_facts(
            request
        ):
            return NewsGenerationResponse(
                completeness=CompletenessResult(
                    status="needs_information",
                    missing=[],
                    conflicts=[],
                    known_facts=[],
                ),
                article=None,
                guidance=(
                    "Saya belum memiliki fakta yang cukup untuk membuat berita. "
                    + (
                        "Pencarian web tidak menemukan sumber yang cukup relevan. "
                        if search_attempted
                        else ""
                    )
                    + NewsCreationWorkflow._evidence_guidance(content_type)
                ),
            )

        if request.clarification_completed:
            completeness = CompletenessResult(
                status="ready",
                missing=[],
                conflicts=[],
                known_facts=[
                    f"User clarification: {fact.field} = {fact.value}"
                    for fact in request.user_facts
                ],
            )
        else:
            emit("checking_request", "Memeriksa fakta dan ambiguitas penting…")
            completeness = OllamaService.check_news_completeness(
                information,
                system_prompt=load_skill_prompt("completeness")
                + (
                    "\n\nACTIVE NEWS CATEGORIES (use only these values for any "
                    "category question): "
                    + ", ".join(request.available_categories)
                    if request.available_categories
                    else ""
                ),
                content_type=content_type,
            )
            if completeness.status != "ready":
                for missing in completeness.missing:
                    if missing.field.lower() == "category" and request.available_categories:
                        missing.options = request.available_categories
                        missing.selection_type = "single"
                completeness.missing = [
                    missing
                    for missing in completeness.missing
                    if missing.field.lower()
                    not in {"topic", "tone", "format", "report_type"}
                ]
                if not completeness.missing and not completeness.conflicts:
                    completeness.status = "ready"
                else:
                    tool_calls = NewsCreationWorkflow._choice_tools(completeness)
                    return NewsGenerationResponse(
                        completeness=completeness,
                        article=None,
                        tool_call=tool_calls[0] if tool_calls else None,
                        tool_calls=tool_calls,
                        web_sources=web_sources,
                    )

        emit("drafting_article", "Menyusun draf berita dari sumber yang disetujui…")
        article = OllamaService.write_news(
            text=information,
            language=request.language,
            tone=request.tone,
            instructions=request.instructions,
            system_prompt=load_skill_prompt("generation")
            + (
                "\n\nClarification has already been completed. Generate now; "
                "never ask another question. Disclose conservative assumptions."
                if request.clarification_completed
                else ""
            )
            + (
                "\n\nChoose exactly one category from this approved list and return "
                f"it in category: {', '.join(request.available_categories)}."
                if request.available_categories
                else ""
            ),
            content_type=content_type,
        )
        emit("evaluating_quality", "Menilai akurasi, kelengkapan, dan kualitas draf…")
        try:
            quality = OllamaService.evaluate_news_quality(
                article=article,
                evidence=information,
                user_request=request.instructions,
            )
        except (AIServiceError, ValueError):
            quality = None
            article.warnings.append(
                "Evaluasi kualitas otomatis tidak tersedia; tinjauan manual diperlukan."
            )
        emit("finalizing", "Memeriksa atribusi, sitasi, dan format artikel…")
        return NewsGenerationResponse(
            completeness=completeness,
            article=article,
            web_sources=web_sources,
            quality=quality,
        )

    @staticmethod
    def _has_usable_user_facts(request: NewsRequest) -> bool:
        editorial_fields = {
            "category",
            "topic",
            "tone",
            "format",
            "report_type",
            "subject_intent",
            "web_source_approval",
        }
        return any(
            fact.field.lower() not in editorial_fields and len(fact.value.strip()) >= 12
            for fact in request.user_facts
        )

    @staticmethod
    def _infer_content_type(query: str) -> NewsContentType:
        value = query.lower()
        patterns: list[tuple[NewsContentType, tuple[str, ...]]] = [
            ("historical_profile", ("sejarah", "history", "historical", "asal usul", "asal-usul", "profil", "profile")),
            ("announcement", ("pengumuman", "announcement", "imbauan resmi")),
            ("regulation_summary", ("peraturan", "regulation", "undang-undang", "surat keputusan", "kebijakan")),
            ("data_report", ("laporan data", "data report", "statistik", "dataset", "spreadsheet")),
            ("public_awareness", ("kesadaran", "awareness", "edukasi publik", "panduan publik")),
            ("event_report", ("laporan acara", "event report", "kegiatan", "acara")),
        ]
        for content_type, markers in patterns:
            if any(marker in value for marker in markers):
                return content_type
        return "news_article"

    @staticmethod
    def _evidence_guidance(content_type: NewsContentType) -> str:
        if content_type == "historical_profile":
            return (
                "Unggah atau pilih sumber sejarah, atau berikan fakta tentang asal-usul, "
                "tonggak perkembangan, lokasi, dan sumber rujukannya. Saya tidak akan "
                "memaksa artikel sejarah memakai tanggal dan pelaku kejadian terkini."
            )
        if content_type == "data_report":
            return (
                "Unggah atau pilih data, lalu sertakan cakupan, periode, angka utama, "
                "dan sumber datanya. Topik saja belum cukup."
            )
        if content_type == "regulation_summary":
            return (
                "Unggah atau pilih peraturan, atau berikan judul/nomor, penerbit, tanggal, "
                "dan ketentuan utamanya. Topik saja belum cukup."
            )
        return (
            "Unggah atau pilih dokumen/informasi, atau jelaskan kejadian nyata dengan "
            "menyebutkan apa yang terjadi, siapa yang terlibat, lokasi, dan waktunya. "
            "Topik atau kategori saja belum cukup."
        )

    @staticmethod
    def _choice_tools(
        completeness: CompletenessResult,
    ) -> list[AskUserChoiceToolCall]:
        return [
            AskUserChoiceToolCall(
                arguments=AskUserChoice(
                    lead_in=missing.reason
                    or "Ada satu keputusan penting sebelum melanjutkan.",
                    question=missing.question,
                    options=missing.options
                    or [
                        "Gunakan asumsi paling netral",
                        "Lanjutkan dengan keterbatasan yang dijelaskan",
                    ],
                    select_type="multi"
                    if missing.selection_type == "multi"
                    else "single",
                    field=missing.field,
                )
            )
            for missing in completeness.missing[:3]
        ]

    @staticmethod
    def _source_approval_response(
        sources: list[WebSearchResult],
    ) -> NewsGenerationResponse:
        missing = MissingInformation(
            field="web_source_approval",
            importance="required",
            kind="format_choice",
            reason=f"Ditemukan {len(sources)} sumber web. Sumber harus disetujui moderator sebelum digunakan.",
            question="Apakah sumber web ini boleh digunakan untuk draf?",
            selection_type="single",
            options=["Gunakan sumber web ini", "Jangan gunakan sumber web"],
        )
        completeness = CompletenessResult(
            status="needs_information",
            missing=[missing],
            conflicts=[],
            known_facts=[],
        )
        tool_calls = NewsCreationWorkflow._choice_tools(completeness)
        return NewsGenerationResponse(
            completeness=completeness,
            article=None,
            tool_call=tool_calls[0],
            tool_calls=tool_calls,
            web_sources=sources,
        )

    @staticmethod
    def _append_web_sources(
        information: str,
        sources: list[WebSearchResult],
    ) -> str:
        blocks = [
            "\n".join(
                [
                    f"[web_source: {source.url}]",
                    f"Title: {source.title}",
                    f"Published: {source.published_at or 'unknown'}",
                    f"Snippet: {source.snippet}",
                ]
            )
            for source in sources
        ]
        return f"{information}\n\nAPPROVED WEB SOURCES:\n" + "\n\n".join(blocks)
