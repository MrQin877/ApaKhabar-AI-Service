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
- Create multiple information items when the document contains distinct topics.
- Use only the information types allowed by the response schema.
- Write a concise title and a one-to-two sentence summary.
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
    def check_news_completeness(text: str) -> CompletenessResult:
        if not text.strip():
            raise ValueError("Information cannot be empty.")

        system_prompt = """
You check whether supplied information is sufficient for a factual news draft.

Required facts are: what happened, who was involved or supplied the information,
where it happened, and when it happened. Mark genuinely useful absent facts as
missing. Do not report a field as missing if the text clearly supplies it. Ask one
short, specific question for each missing field. Put contradictions in conflicts.
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
    ) -> NewsArticle:
        if not text.strip():
            raise ValueError("Information cannot be empty.")

        language_name = "Bahasa Melayu" if language == "ms" else "English"
        system_prompt = f"""
You write accurate news articles in {language_name} with a {tone} tone.

Use only facts explicitly present in the supplied information. Never invent names,
dates, numbers, explanations, sources, or quotations. Preserve uncertainty and
attribute claims when attribution is supplied. Write the most important verified
fact first. Body must contain an ordered list of publishable paragraphs. Include
source identifiers in sources_used when the input contains markers such as page,
sheet, row, paragraph, or filename. Put any limitation in warnings. The language
field must be {language}.
""".strip()
        result = OllamaService._structured_chat(
            NewsArticle,
            system_prompt,
            text,
            temperature=0.2,
        )
        article = NewsArticle.model_validate(result)
        if not re.search(r"\[source:\s*[^\]]+\]", text, re.IGNORECASE):
            article.sources_used = []
        return article

    @staticmethod
    def summarize(text: str) -> str:
        if not text.strip():
            raise ValueError("Document content cannot be empty.")

        settings = get_settings()

        try:
            response = OllamaService._client().chat(
                model=settings.ollama_generation_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Summarize the supplied document in two or three "
                            "clear sentences. Use only supported facts and do "
                            "not add commentary."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                stream=False,
                think=False,
                options={"temperature": 0},
            )
        except ResponseError as exc:
            raise AIServiceError(f"Ollama request failed: {exc}") from exc
        except (ConnectionError, OSError) as exc:
            raise AIServiceError("Ollama is unavailable.") from exc

        summary = response.message.content.strip()
        if not summary:
            raise AIServiceError("Ollama returned an empty summary.")

        return summary
