"""Provider adapters. Graphs use validated schemas, never provider-specific messages."""
from functools import lru_cache
import hashlib
import json
import logging
import time
import requests
from ollama import Client
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
        return s.llama_cpp_model if s.ai_provider == "llama_cpp" else s.ollama_generation_model

    def structured(self, schema: type[BaseModel], system: str, data: str, temperature=0):
        messages = [{"role": "system", "content": system}, {"role": "user", "content": data}]
        # One bounded repair attempt; malformed responses never reach tools or storage.
        for attempt in range(2):
            try:
                started = time.perf_counter()
                logger.info("Model request started: schema=%s attempt=%d provider=%s model=%s",
                            schema.__name__, attempt + 1, self.settings.ai_provider, self.name)
                try:
                    raw = self._chat(messages, schema.model_json_schema(), temperature)
                finally:
                    logger.info("Model request ended: schema=%s attempt=%d elapsed_seconds=%.2f",
                                schema.__name__, attempt + 1, time.perf_counter() - started)
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
            if s.ai_provider == "ollama":
                result = Client(host=s.ollama_base_url, timeout=s.llama_cpp_timeout_seconds).chat(
                    model=self.name, messages=messages, format=schema, stream=False, think=False,
                    options={"temperature": temperature, "num_predict": s.llama_cpp_max_tokens})
                return result.message.content
            payload = {"model": self.name, "messages": messages, "temperature": temperature,
                       "max_tokens": s.llama_cpp_max_tokens, "stream": False}
            if schema:
                payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "response", "schema": schema}}
            headers = {"Authorization": f"Bearer {s.llama_cpp_api_key}"} if s.llama_cpp_api_key else {}
            response = requests.post(s.llama_cpp_base_url.rstrip("/") + "/chat/completions",
                                     json=payload, headers=headers, timeout=s.llama_cpp_timeout_seconds)
            if not response.ok and any(marker in response.text.lower() for marker in (
                    "exceeds the available context", "context_length_exceeded", "exceed_context_size")):
                raise ModelError("Model context limit exceeded. Reduce request context or increase the model server context window.")
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except ModelError:
            raise
        except Exception as exc:
            raise ModelError(f"Generation provider {s.ai_provider} failed ({type(exc).__name__})") from exc


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
        name = s.ollama_embedding_model if s.embedding_provider == "ollama" else s.embedding_model
        return hashlib.sha256(f"{s.embedding_provider}:{name}:{s.embedding_dimensions}".encode()).hexdigest()[:16]

    def encode(self, texts: list[str], query=False):
        s = self.settings
        try:
            if s.embedding_provider == "ollama":
                return Client(host=s.ollama_base_url, timeout=s.llama_cpp_timeout_seconds).embed(
                    model=s.ollama_embedding_model, input=texts).embeddings
            if s.embedding_provider == "embedding_gemma":
                model = _sentence_model(s.embedding_model, s.embedding_device)
                method = model.encode_query if query else model.encode_document
                return method(texts, normalize_embeddings=True, truncate_dim=s.embedding_dimensions).tolist()
            headers = {"Authorization": f"Bearer {s.embedding_api_key}"} if s.embedding_api_key else {}
            response = requests.post(s.embedding_base_url.rstrip("/") + "/embeddings",
                                     headers=headers, json={"model": s.embedding_model, "input": texts}, timeout=120)
            response.raise_for_status()
            return [item["embedding"] for item in sorted(response.json()["data"], key=lambda item: item["index"])]
        except Exception as exc:
            raise ModelError(f"Embedding provider {s.embedding_provider} failed ({type(exc).__name__})") from exc
