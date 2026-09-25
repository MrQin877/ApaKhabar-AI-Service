from typing import Any

import requests

from app.services.model_providers.base import GenerationProvider, ModelProviderError


class OpenAICompatibleProvider(GenerationProvider):
    """Shared client for self-hosted OpenAI-compatible model servers."""

    def __init__(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: str | None,
        model_name: str,
        timeout_seconds: int,
        max_tokens: int,
    ) -> None:
        self.provider_name = provider_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self._session = requests.Session()

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        if response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "apakhabar_response",
                    "schema": response_schema,
                    "strict": True,
                },
            }

        try:
            response = self._session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            choice = body["choices"][0]
            content = choice["message"]["content"]
            if choice.get("finish_reason") == "length":
                raise ModelProviderError(
                    f"{self.provider_name} reached its {self.max_tokens}-token "
                    "output limit before completing the response."
                )
        except requests.Timeout as exc:
            raise ModelProviderError(
                f"{self.provider_name} did not finish before the configured timeout."
            ) from exc
        except requests.RequestException as exc:
            detail = ""
            if exc.response is not None:
                detail = f" HTTP {exc.response.status_code}: {exc.response.text[:500]}"
            raise ModelProviderError(
                f"{self.provider_name} request failed.{detail}"
            ) from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelProviderError(
                f"{self.provider_name} returned an invalid response payload."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise ModelProviderError(f"{self.provider_name} returned an empty response.")

        return content.strip()
