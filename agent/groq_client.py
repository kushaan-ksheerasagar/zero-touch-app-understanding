"""
Groq API client adapter for autonomous Android app exploration.

Provides a lightweight, provider-neutral wrapper around the official `groq` SDK,
adhering to the client interface expected by LLMReasoner.
"""

import os
import re
from typing import Any, Dict, Optional

DEFAULT_GROQ_MODEL: str = "llama-3.3-70b-versatile"


class GroqLLMClient:
    """
    Groq client adapter for LLMReasoner.

    Exposes .generate(prompt) -> str requesting structured JSON output from Groq.
    Reads credentials from the GROQ_API_KEY environment variable. Never logs or leaks secrets.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 30.0,
        temperature: float = 0.0,
        client: Optional[Any] = None,
    ) -> None:
        """
        Initialize GroqLLMClient.

        :param api_key: Optional Groq API key. If omitted, read from GROQ_API_KEY env var.
        :param model_name: Target model identifier. Defaults to GROQ_MODEL env var or llama-3.3-70b-versatile.
        :param timeout: Request timeout in seconds.
        :param temperature: Sampling temperature (default 0.0 for deterministic reasoning).
        :param client: Optional pre-configured or mock Groq client instance.
        """
        self.timeout = timeout
        self.temperature = temperature
        self.model_name = (
            model_name
            or os.environ.get("GROQ_MODEL")
            or DEFAULT_GROQ_MODEL
        )

        if client is not None:
            self.client = client
            self._api_key = api_key or "<injected_client>"
        else:
            resolved_key = api_key or os.environ.get("GROQ_API_KEY")
            if not resolved_key or not str(resolved_key).strip():
                raise ValueError(
                    "GROQ_API_KEY is not set. Please provide 'api_key' or set the GROQ_API_KEY environment variable."
                )
            self._api_key = str(resolved_key).strip()

            try:
                import groq
                self.client = groq.Groq(
                    api_key=self._api_key,
                    timeout=self.timeout,
                )
            except ImportError as err:
                raise ImportError(
                    "The 'groq' package is required to use GroqLLMClient. Please install it with 'pip install groq'."
                ) from err

    def _sanitize_error_message(self, message: str) -> str:
        """Removes any API key patterns or authorization headers from error messages."""
        if not message:
            return ""
        # Redact Groq API key pattern (gsk_...)
        sanitized = re.sub(r"gsk_[A-Za-z0-9]+", "[REDACTED_API_KEY]", message)
        # Redact Bearer tokens
        sanitized = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", sanitized, flags=re.IGNORECASE)
        # Redact actual key if known
        if self._api_key and len(self._api_key) > 6 and self._api_key != "<injected_client>":
            sanitized = sanitized.replace(self._api_key, "[REDACTED_API_KEY]")
        return sanitized

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Sends the compact reasoning prompt to Groq requesting strict JSON output.

        :param prompt: Formatted reasoning prompt.
        :return: Raw JSON string returned by the model.
        """
        model = kwargs.get("model", self.model_name)
        temperature = kwargs.get("temperature", self.temperature)
        timeout = kwargs.get("timeout", self.timeout)

        try:
            chat_completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
                timeout=timeout,
            )

            if not chat_completion or not getattr(chat_completion, "choices", None):
                raise RuntimeError("Groq API returned an empty response with no choices.")

            choice = chat_completion.choices[0]
            message = getattr(choice, "message", None)
            content = getattr(message, "content", None) if message else None

            if content is None:
                raise RuntimeError("Groq API returned a message with null content.")

            return str(content)

        except Exception as exc:
            sanitized_msg = self._sanitize_error_message(str(exc))
            raise RuntimeError(
                f"Groq API error ({type(exc).__name__}): {sanitized_msg}"
            ) from exc

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        """Callable protocol support for LLMReasoner."""
        return self.generate(prompt, **kwargs)
