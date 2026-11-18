"""Provider adapters. Graphs use validated schemas, never provider-specific messages."""
from functools import lru_cache
import hashlib
import json
import logging
import math
import re
import time
from urllib.parse import urlsplit
import requests
from pydantic import BaseModel, ValidationError
from app.core.config import get_settings


logger = logging.getLogger("uvicorn.error")


class ModelError(RuntimeError):
    pass


class GenerationModel:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.call_count = 0

    @property
    def name(self):
        s = self.settings
        return s.ai_model

    def structured(self, schema: type[BaseModel], system: str, data: str, temperature=0):
        messages = [{"role": "system", "content": system}, {"role": "user", "content": data}]
        # One bounded repair attempt; malformed responses never reach tools or storage.
        for attempt in range(2):
            try:
                started = time.perf_counter()
                logger.info("Model request started: schema=%s attempt=%d provider=%s model=%s",
                            schema.__name__, attempt + 1, urlsplit(self.settings.ai_base_url).hostname, self.name)
                try:
                    raw = self._chat(messages, schema.model_json_schema(), temperature)
                except ModelError as exc:
                    # ModelError contains bounded provider identifiers, not source text.
                    logger.warning("Model request failed: schema=%s attempt=%d error=%s",
                                   schema.__name__, attempt + 1, exc)
                    raise
                finally:
                    logger.info("Model request ended: schema=%s attempt=%d elapsed_seconds=%.2f",
                                schema.__name__, attempt + 1, time.perf_counter() - started)
                if (urlsplit(self.settings.ai_base_url).hostname == "generativelanguage.googleapis.com"
                        and self.name.startswith("gemma-") and isinstance(raw, str)):
                    # Hosted Gemma may prepend a complete thought block even in
                    # JSON mode. Never recover JSON from inside an unfinished thought.
                    raw = re.sub(r'\A\s*<thought>.*?</thought>\s*', '', raw, count=1, flags=re.DOTALL)
                    fenced = re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*', raw, flags=re.DOTALL)
                    if fenced:
                        raw = fenced.group(1)
                return schema.model_validate_json(raw)
            except ValidationError as exc:
                logger.warning("Model schema validation failed: schema=%s attempt=%d retrying=%s",
                               schema.__name__, attempt + 1, not bool(attempt))
                # Keep diagnostics useful without exposing source text or rejected values.
                errors = [{"field": ".".join(map(str, error["loc"])) or "$",
                           "type": error["type"]}
                          for error in exc.errors(include_input=False, include_url=False)][:20]
                if attempt:
                    raise ModelError(f"Model output did not match {schema.__name__}: "
                                     + json.dumps(errors, ensure_ascii=False)) from exc
                # Regenerate from the original evidence instead of appending a potentially
                # max-length rejected response to an already large context.
                messages = [{"role": "system", "content": system +
                    "\nThe previous attempt failed schema validation. Regenerate a complete JSON object "
                    "from the supplied evidence, correcting these field errors. Do not invent facts or "
                    "add markdown/commentary. Validation errors: " + json.dumps(errors, separators=(",", ":"))},
                    {"role": "user", "content": data}]
        raise ModelError("No structured response")

    def text(self, system: str, data: str):
        return self._chat([{"role": "system", "content": system}, {"role": "user", "content": data}], None, 0)

    def _chat(self, messages, schema, temperature):
        self.call_count += 1
        s = self.settings
        try:
            if not s.ai_api_key.strip() or not s.ai_model.strip():
                raise ModelError("Configure the API key and model for this writer/evaluator endpoint before generating.")
            payload = {"model": self.name, "messages": messages, "temperature": temperature,
                       "max_tokens": s.ai_max_tokens, "stream": False}
            if urlsplit(s.ai_base_url).hostname == "api.openai.com" and self.name.startswith(("gpt-5", "o1", "o3", "o4")):
                payload["max_completion_tokens"] = payload.pop("max_tokens")
                payload.pop("temperature")
            if schema:
                if (urlsplit(s.ai_base_url).hostname == "generativelanguage.googleapis.com"
                        and self.name.startswith("gemma-")):
                    # Hosted Gemma accepts JSON mode but rejects some nested schemas
                    # (including our extraction schema). Keep full local validation.
                    payload["messages"] = [{**message} for message in messages]
                    payload["messages"][0]["content"] += (
                        "\nReturn only a JSON object matching this JSON Schema. "
                        "Do not include markdown fences or commentary.\n"
                        + json.dumps(schema, ensure_ascii=False))
                    payload["response_format"] = {"type": "json_object"}
                else:
                    payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "response", "schema": schema}}
            headers = {"Authorization": f"Bearer {s.ai_api_key}"} if s.ai_api_key else {}
            deadline = time.monotonic() + s.ai_timeout_seconds
            for attempt in range(3):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise requests.Timeout()
                response = requests.post(s.ai_base_url.rstrip("/") + "/chat/completions",
                                         json=payload, headers=headers, timeout=remaining)
                if response.ok or response.status_code not in (500, 502, 503, 504) or attempt == 2:
                    break
                delay = 2 ** attempt
                if deadline - time.monotonic() <= delay:
                    break
                logger.warning("Generation API temporary failure: host=%s model=%s HTTP=%s retry=%d/2 delay=%ss",
                               urlsplit(s.ai_base_url).hostname, self.name,
                               response.status_code, attempt + 1, delay)
                time.sleep(delay)
            if not response.ok and any(marker in response.text.lower() for marker in (
                    "exceeds the available context", "context_length_exceeded", "exceed_context_size")):
                raise ModelError("Model context limit exceeded. Reduce request context or increase the model server context window.")
            if not response.ok:
                # Only expose bounded identifiers, never provider messages that can
                # contain credentials, source text, or rejected request values.
                try:
                    body = response.json()
                    if isinstance(body, list):
                        body = body[0] if body else {}
                    error = body.get("error", {}) if isinstance(body, dict) else {}
                    error = error if isinstance(error, dict) else {}
                except (ValueError, AttributeError):
                    error = {}
                import re
                identifiers = {key: value for key in ("code", "status", "type", "param")
                               if isinstance(value := error.get(key), str)
                               and re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", value)}
                host = urlsplit(s.ai_base_url).hostname or "configured endpoint"
                hint = ""
                if identifiers.get("code") in {"credit_balance_exhausted", "insufficient_quota"} or identifiers.get("type") == "insufficient_quota":
                    hint = " API credits/quota exhausted; check this provider's billing balance before retrying."
                raise ModelError(f"Generation API {host} model={self.name} returned HTTP {response.status_code} "
                                 + json.dumps(identifiers, sort_keys=True) + hint)
            return response.json()["choices"][0]["message"]["content"]
        except ModelError:
            raise
        except requests.Timeout as exc:
            host = urlsplit(s.ai_base_url).hostname or "configured endpoint"
            raise ModelError(f"Generation API {host} model={self.name} timed out "
                             f"(configured timeout: {s.ai_timeout_seconds:g}s; {type(exc).__name__}).") from exc
        except Exception as exc:
            raise ModelError(f"Generation API {urlsplit(s.ai_base_url).hostname} model={self.name} failed ({type(exc).__name__})") from exc


@lru_cache(maxsize=2)
def _sentence_model(name, device):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name, device=None if device == "auto" else device, local_files_only=True)


class Embeddings:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    @property
    def fingerprint(self):
        s = self.settings
        name = s.embedding_model
        return hashlib.sha256(f"{s.embedding_provider}:{name}:{s.embedding_dimensions}".encode()).hexdigest()[:16]

    def encode(self, texts: list[str], query=False):
        s = self.settings
        try:
            if s.embedding_provider == "embedding_gemma":
                model = _sentence_model(s.embedding_model, s.embedding_device)
                method = model.encode_query if query else model.encode_document
                return method(texts, normalize_embeddings=True, truncate_dim=s.embedding_dimensions).tolist()
            if s.embedding_provider == "gemini":
                if not s.embedding_api_key.strip():
                    raise ModelError("Configure EMBEDDING_API_KEY for Gemini embeddings.")
                from google import genai
                from google.genai import types
                vectors = []
                client = genai.Client(api_key=s.embedding_api_key)
                try:
                    for start in range(0, len(texts), 50):
                        batch = texts[start:start + 50]
                        response = client.models.embed_content(
                            model=s.embedding_model,
                            contents=batch,
                            config=types.EmbedContentConfig(
                                task_type="RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT",
                                output_dimensionality=s.embedding_dimensions,
                            ),
                        )
                        embeddings = response.embeddings or []
                        if len(embeddings) != len(batch):
                            raise ModelError("Gemini returned an unexpected number of embeddings.")
                        for item in embeddings:
                            values = item.values or []
                            if len(values) != s.embedding_dimensions:
                                raise ModelError("Gemini returned an unexpected embedding dimension.")
                            # gemini-embedding-001 needs normalization below 3072 dimensions.
                            length = math.sqrt(sum(value * value for value in values))
                            if not length or not math.isfinite(length):
                                raise ModelError("Gemini returned an invalid embedding vector.")
                            vectors.append([value / length for value in values])
                finally:
                    client.close()
                return vectors
            headers = {"Authorization": f"Bearer {s.embedding_api_key}"} if s.embedding_api_key else {}
            response = requests.post(s.embedding_base_url.rstrip("/") + "/embeddings",
                                     headers=headers, json={"model": s.embedding_model, "input": texts}, timeout=120)
            response.raise_for_status()
            return [item["embedding"] for item in sorted(response.json()["data"], key=lambda item: item["index"])]
        except ModelError:
            raise
        except Exception as exc:
            raise ModelError(f"Embedding provider {s.embedding_provider} failed ({type(exc).__name__})") from exc
