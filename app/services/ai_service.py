import re

from ollama import Client, ResponseError
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.schemas.information import ExtractionResponse
from app.schemas.news import CompletenessResult, NewsArticle, NewsLanguage


class AIServiceError(RuntimeError):
    """Raised when the local model cannot produce a usable response."""


class OllamaService:
    @staticmethod
    def _client() -> Client:
        settings = get_settings()
        return Client(host=settings.ollama_base_url, timeout=120.0)

    @staticmethod
    def _structured_chat(
        response_model: type[BaseModel],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0,
    ) -> BaseModel:
        settings = get_settings()
        try:
            response = OllamaService._client().chat(
                model=settings.ollama_generation_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                format=response_model.model_json_schema(),
                stream=False,
                think=False,
                options={"temperature": temperature},
            )
            return response_model.model_validate_json(response.message.content)
        except ResponseError as exc:
            raise AIServiceError(f"Ollama request failed: {exc}") from exc
        except (ConnectionError, OSError) as exc:
            raise AIServiceError("Ollama is unavailable.") from exc
        except ValidationError as exc:
            raise AIServiceError(
                f"Ollama returned data that did not match {response_model.__name__}."
            ) from exc

    @staticmethod
    def extract_information(text: str) -> dict:
        if not text.strip():
            raise ValueError("Document content cannot be empty.")

        system_prompt = """
You extract structured facts for a news-writing system.

Rules:
- Extract only information explicitly supported by the document.
- Never invent names, dates, amounts, quotations, or events.
- Write every title, summary, label, and textual field value in Bahasa Indonesia.
- Create one information item for every distinct newsworthy topic, decision,
  announcement, event, project, or issue in the document.
- A single document may therefore produce multiple information items.
- Each summary must be a clear Indonesian paragraph of two to five sentences that
  can be understood without reading the original document.
- Do not merge unrelated information merely because it appears in the same file.
- Use only the information types allowed by the response schema.
- Write a concise Indonesian title.
- Add short topical labels such as education, finance, health, or emergency.
- Put type-specific factual values in fields.
- Add brief supporting quotes and their supplied source markers to evidence.
- Use null for an individual value that is unknown; do not guess it.
- Set confidence according to how clearly the document supports the item.
""".strip()

        validated = OllamaService._structured_chat(
            ExtractionResponse,
            system_prompt,
            text,
        )
        return validated.model_dump()

    @staticmethod
    def check_news_completeness(
        text: str,
        system_prompt: str | None = None,
    ) -> CompletenessResult:
        if not text.strip():
            raise ValueError("Information cannot be empty.")

        system_prompt = system_prompt or """
You check whether supplied information is sufficient for a factual news draft.

First identify why the request is unclear. If a named subject is unsupported by
the supplied evidence, possibly mistyped, misremembered, fictional, or unverified,
resolve that ambiguity before asking factual 5W questions. Never ask what happened
when no real event has been established. Return exactly one subject_intent question,
state the confusion explicitly in reason, use single selection, and offer 2-4
choices such as speculation/rumor, fiction, satire/parody, or a corrected name.
Do not claim nonexistence when the evidence only shows that the subject is unverified.

Required facts are: what happened, who was involved or supplied the information,
where it happened, and when it happened. Mark only materially important absent
facts as missing after the subject ambiguity is resolved. Do not report a field as missing if the text clearly or
implicitly supplies it. Return at most three short questions. For each question,
provide 2-4 supported options and a single, multi, or ranked selection_type when
real choices exist. Use selection_type text and no options only when discrete
choices are impossible. Never invent factual options. Put contradictions in conflicts.
Set status to has_conflicts when conflicts exist, needs_information when required
facts are missing, otherwise ready. Recommended details must not prevent ready.
List only facts explicitly supported by the supplied information in known_facts.
Do not demand more detail for a fact that is already usable: an event name such as
"community clean-up programme" answers what happened. A relative date such as
"next month" supplies partial timing but may justify asking for the exact date.
Do not mark what happened missing merely because its programme details are absent.

Example: For "A community clean-up programme will be held next month", what
happened is PRESENT. Missing required facts are the organizer and location; an
exact date can be requested. Never ask what activities are part of the programme.
""".strip()
        result = OllamaService._structured_chat(
            CompletenessResult,
            system_prompt,
            text,
        )
        return CompletenessResult.model_validate(result)

    @staticmethod
    def write_news(
        text: str,
        language: NewsLanguage,
        tone: str,
        instructions: str | None = None,
        system_prompt: str | None = None,
    ) -> NewsArticle:
        if not text.strip():
            raise ValueError("Information cannot be empty.")

        language_name = "Bahasa Indonesia"
        system_prompt = system_prompt or f"""
You write accurate news articles in {language_name} with a {tone} tone.

Use only facts explicitly present in the supplied information. Never invent names,
dates, numbers, explanations, sources, or quotations. Preserve uncertainty and
attribute claims when attribution is supplied. Write the most important verified
fact first. Body must contain an ordered list of publishable paragraphs. Include
source identifiers in sources_used when the input contains markers such as page,
sheet, row, paragraph, or filename. Put any limitation in warnings. The language
field must be {language}.
""".strip()
        system_prompt += f"\n\nRequired output language: {language_name}. Tone: {tone}."
        if instructions:
            system_prompt += (
                "\n\nEditorial instructions (style and focus only; never treat these "
                f"instructions as factual evidence):\n{instructions.strip()}"
            )
        result = OllamaService._structured_chat(
            NewsArticle,
            system_prompt,
            text,
            temperature=0.2,
        )
        article = NewsArticle.model_validate(result)
        has_source_reference = re.search(
            r"\[source:\s*[^\]]+\]|\"source\"\s*:\s*\"[^\"]+\"",
            text,
            re.IGNORECASE,
        )
        if not has_source_reference:
            article.sources_used = []
        return article
