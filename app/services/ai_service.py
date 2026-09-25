import json
import re

from pydantic import BaseModel, ValidationError

from app.schemas.information import ExtractionContext, ExtractionResponse
from app.schemas.news import (
    CompletenessResult,
    NewsArticle,
    NewsLanguage,
    NewsContentType,
    NewsRevisionRequest,
    NewsQualityAssessment,
    NewsQualityEvaluation,
)
from app.services.model_providers import get_generation_provider
from app.services.model_providers.base import ModelProviderError


class AIServiceError(RuntimeError):
    """Raised when the local model cannot produce a usable response."""


class AIService:
    @staticmethod
    def _structured_chat(
        response_model: type[BaseModel],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0,
    ) -> BaseModel:
        provider = get_generation_provider()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            content = provider.generate(
                messages=messages,
                response_schema=response_model.model_json_schema(),
                temperature=temperature,
            )
        except ModelProviderError as exc:
            raise AIServiceError(str(exc)) from exc

        try:
            return response_model.model_validate_json(
                AIService._clean_json_response(content)
            )
        except (ValidationError, json.JSONDecodeError):
            repair_messages = messages + [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        "Your previous response was invalid. Correct only its JSON "
                        "structure and schema violations. Preserve supported facts, "
                        "do not add new facts, return exactly one JSON object, and do "
                        "not use Markdown fences."
                    ),
                },
            ]
            try:
                repaired = provider.generate(
                    messages=repair_messages,
                    response_schema=response_model.model_json_schema(),
                    temperature=0,
                )
                return response_model.model_validate_json(
                    AIService._clean_json_response(repaired)
                )
            except ModelProviderError as exc:
                raise AIServiceError(str(exc)) from exc
            except (ValidationError, json.JSONDecodeError) as exc:
                raise AIServiceError(
                    "The configured model returned invalid structured data twice "
                    f"for {response_model.__name__}."
                ) from exc

        except (TypeError, ValueError) as exc:
            raise AIServiceError(
                "The configured model returned data that did not match "
                f"{response_model.__name__}."
            ) from exc

    @staticmethod
    def _clean_json_response(content: str) -> str:
        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return cleaned[start : end + 1]
        return cleaned

    @staticmethod
    def extract_information(
        text: str,
        context: ExtractionContext | None = None,
    ) -> dict:
        if not text.strip():
            raise ValueError("Document content cannot be empty.")

        context = context or ExtractionContext()
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

        if context.mode == "targeted":
            if not context.effective_query():
                raise ValueError("Targeted extraction requires a meaningful query or keyword.")
            system_prompt += f"""

TARGETED EXTRACTION MODE
Extract information that directly answers the user's request. Keywords are
retrieval hints, not factual evidence. Do not discard a supported synonym merely
because it does not repeat an exact keyword.

User request: {context.query or ''}
Keywords: {', '.join(context.keywords) or 'none'}
"""
        else:
            system_prompt += """

GENERAL EXTRACTION MODE
Inspect all supplied sections and extract every distinct, meaningful, newsworthy,
or reusable information item. Merge duplicate descriptions of the same matter,
but never combine unrelated topics. Ignore headers, footers, signatures, repeated
boilerplate, and formatting-only text.
"""

        validated = AIService._structured_chat(
            ExtractionResponse,
            system_prompt,
            text,
        )
        return validated.model_dump()

    @staticmethod
    def check_news_completeness(
        text: str,
        system_prompt: str | None = None,
        content_type: NewsContentType = "news_article",
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
        system_prompt += (
            "\n\nCONTENT FORMAT: " + content_type + ". Judge completeness for this "
            "format, not automatically as a current event report."
        )
        result = AIService._structured_chat(
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
        content_type: NewsContentType = "news_article",
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

Keep the result concise and complete. Write 3-7 body paragraphs, with no paragraph
longer than 120 words. Do not repeat facts to increase length. Finish every JSON
field and close the JSON object before the output limit.
""".strip()
        system_prompt += (
            f"\n\nRequired output language: {language_name}. Tone: {tone}. "
            f"Content format: {content_type}. Return this exact value in content_type."
        )
        if instructions:
            system_prompt += (
                "\n\nEditorial instructions (style and focus only; never treat these "
                f"instructions as factual evidence):\n{instructions.strip()}"
            )
        result = AIService._structured_chat(
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

    @staticmethod
    def evaluate_news_quality(
        article: NewsArticle,
        evidence: str,
        user_request: str | None = None,
    ) -> NewsQualityEvaluation:
        """Estimate draft quality against the evidence supplied to generation.

        The model supplies dimension judgements and claim checks. Application code
        calculates the weighted total and blocking rules so model arithmetic cannot
        change the configured quality formula.
        """
        if not evidence.strip():
            raise ValueError("Evidence cannot be empty.")

        system_prompt = """
You are a strict Indonesian news quality evaluator. Evaluate the supplied draft
only against APPROVED EVIDENCE and the USER REQUEST. This is an estimate for a
human moderator, not a guarantee of correctness.

Return all seven dimensions as scores from 0 to 100 with a concise explanation
and concrete issues. Do not calculate an overall or weighted score.

Scoring rules:
- accuracy: factual grounding. Extract the draft's factual claims and compare
  each with approved evidence. Unsupported and contradicted claims must reduce
  this score substantially. Style instructions are never factual evidence.
- completeness: coverage of applicable, available 5W1H facts. Do not penalize a
  detail that the evidence itself does not contain.
- relevance: alignment with the user request and approved evidence.
- readability: clarity, paragraph flow, repetition, and sentence quality.
- structure: headline, lead, body, inverted-pyramid ordering, category, and
  source attribution where sources exist.
- language: formal, natural Bahasa Indonesia, consistent terminology, dates,
  and numbers. Preserve proper names.
- safety: defamation risk, unsupported accusations, privacy exposure, hate,
  sexual/graphic content, dangerous instructions, and inflammatory wording.

For every externally verifiable factual assertion, add a claim_check with one of
supported, partially_supported, unsupported, or contradicted. A supported claim
must identify its page, filename, row, URL, or other supplied source marker when
available. Never manufacture a source. Use warnings for conflicts, serious safety
concerns, or limitations. Be conservative when evidence is ambiguous.
""".strip()
        payload = {
            "user_request": user_request or "No additional editorial request.",
            "approved_evidence": evidence,
            "draft": article.model_dump(mode="json"),
        }
        assessment = AIService._structured_chat(
            NewsQualityAssessment,
            system_prompt,
            json.dumps(payload, ensure_ascii=False),
            temperature=0,
        )
        return NewsQualityEvaluation.from_assessment(
            NewsQualityAssessment.model_validate(assessment),
            evaluator_model=get_generation_provider().model_name,
        )

    @staticmethod
    def revise_news(request: NewsRevisionRequest) -> NewsArticle:
        prompt = """
Revise an existing Indonesian news draft using the editorial instruction.
Use only facts supported by APPROVED EVIDENCE. Preserve supported facts and
attribution. Never add names, dates, numbers, quotations, causes, or accusations
that do not occur in the evidence. Return the complete revised article schema.
""".strip()
        if request.available_categories:
            prompt += (
                "\nChoose exactly one active category from: "
                + ", ".join(request.available_categories)
            )
        payload = {
            "editorial_instruction": request.instruction,
            "approved_evidence": request.evidence,
            "current_article": request.article.model_dump(mode="json"),
        }
        result = AIService._structured_chat(
            NewsArticle,
            prompt,
            json.dumps(payload, ensure_ascii=False),
            temperature=0.2,
        )
        return NewsArticle.model_validate(result)


# Backward-compatible name used by existing routes, scripts, and integrations.
OllamaService = AIService
