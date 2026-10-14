"""One-shot OpenAI-compatible JSON chat calls using Python's standard library."""

from __future__ import annotations

import json
import http.client
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field


class APIConnectionError(Exception):
    """Safe, credential-free connectivity/authentication error."""


class APIResponseError(Exception):
    """Safe error for a response that is not in the expected protocol."""


@dataclass(frozen=True)
class APIConfig:
    api_key: str = field(repr=False)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-flash"
    timeout: float = 25.0

    def __post_init__(self):
        parsed = urllib.parse.urlsplit(self.base_url)
        if (
            parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
        ):
            raise ValueError("The API endpoint must be an HTTPS URL without credentials, query, or fragment.")
        if not self.api_key.strip() or any(character.isspace() for character in self.api_key):
            raise ValueError("Enter a non-empty API key without whitespace.")
        if not self.model.strip() or len(self.model) > 120:
            raise ValueError("Enter a model name.")
        if not math.isfinite(self.timeout) or not 0 < self.timeout <= 120:
            raise ValueError("Timeout must be between 0 and 120 seconds.")

    @property
    def completion_url(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A 3xx response is an error, so Authorization never follows a redirect.
        return None


class OpenAICompatibleClient:
    """No retries, no logs, no persistence, and no credential-bearing redirects."""

    def __init__(self, config: APIConfig):
        self.config = config
        self._opener = urllib.request.build_opener(_NoRedirect())

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.config.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 700,
            "stream": False,
        }
        # Current DeepSeek non-thinking mode: https://api-docs.deepseek.com/guides/thinking_mode
        # Keep the generic compatible endpoint payload free of provider-specific fields.
        if urllib.parse.urlsplit(self.config.base_url).hostname == "api.deepseek.com":
            payload["thinking"] = {"type": "disabled"}
        request = urllib.request.Request(
            self.config.completion_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Bearer " + self.config.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self.config.timeout) as response:
                body = response.read(1_048_577)
        except urllib.error.HTTPError as error:
            # Do not include the URL, response body, or raw exception (they may echo secrets).
            code = error.code
            error.close()
            raise APIConnectionError(f"The API request failed (HTTP {code}).") from None
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError):
            raise APIConnectionError("The API could not be reached.") from None
        if len(body) > 1_048_576:
            raise APIResponseError("The API response exceeded the supported size.")
        try:
            parsed = json.loads(body.decode("utf-8"))
            content = parsed["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError
            return content
        except (UnicodeError, ValueError, KeyError, IndexError, TypeError):
            raise APIResponseError("The API returned an unsupported response format.") from None
