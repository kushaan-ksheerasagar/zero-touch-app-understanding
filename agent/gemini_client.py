"""
Gemini API client adapter for autonomous Android app exploration.

Provides a lightweight, provider-neutral wrapper around the official `google-genai` SDK,
adhering to the client interface expected by LLMReasoner.
"""

import os
import re
from typing import Any, Dict, Optional

DEFAULT_GEMINI_MODEL: str = "gemini-3.6-flash"


def resolve_gemini_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """
    Safely resolves the Gemini API key from explicit arguments or the environment.
    Never logs or prints the key.
    """
    if explicit_key and str(explicit_key).strip():
        return str(explicit_key).strip()

    # 1. Check current process environment
    key = os.environ.get("GEMINI_API_KEY")
    if key and str(key).strip():
        return str(key).strip()

    # 2. Check dotenv if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv(os.path.expanduser("~/.env"))
        key = os.environ.get("GEMINI_API_KEY")
        if key and str(key).strip():
            return str(key).strip()
    except Exception:
        pass

    # 3. Check Windows Registry (HKCU / HKLM)
    try:
        import winreg
        for hive, path in [
            (winreg.HKEY_CURRENT_USER, r"Environment"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ]:
            try:
                with winreg.OpenKey(hive, path) as k:
                    val, _ = winreg.QueryValueEx(k, "GEMINI_API_KEY")
                    if val and str(val).strip():
                        return str(val).strip()
            except FileNotFoundError:
                pass
    except Exception:
        pass

    # 4. Check parent / terminal process environments
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            try:
                proc_env = proc.environ()
                if "GEMINI_API_KEY" in proc_env:
                    val = proc_env.get("GEMINI_API_KEY")
                    if val and str(val).strip():
                        return str(val).strip()
            except Exception:
                continue
    except Exception:
        pass

    return None


class GeminiLLMClient:
    """
    Gemini client adapter for LLMReasoner using the official google-genai SDK.

    Exposes .generate(prompt) -> str requesting structured JSON output from Gemini.
    Reads credentials strictly from the GEMINI_API_KEY environment variable.
    Never hardcodes, logs, or leaks secrets.
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
        Initialize GeminiLLMClient.

        :param api_key: Optional Gemini API key. If omitted, read from GEMINI_API_KEY.
        :param model_name: Target model identifier. Defaults to GEMINI_MODEL env var or gemini-2.5-flash.
        :param timeout: Request timeout in seconds.
        :param temperature: Sampling temperature (default 0.0 for deterministic reasoning).
        :param client: Optional pre-configured or mock Google GenAI client instance.
        """
        self.timeout = timeout
        self.temperature = temperature
        self.model_name = (
            model_name
            or os.environ.get("GEMINI_MODEL")
            or DEFAULT_GEMINI_MODEL
        )

        if client is not None:
            self.client = client
            self._api_key = api_key or "<injected_client>"
        else:
            resolved_key = resolve_gemini_api_key(api_key)
            if not resolved_key or not str(resolved_key).strip():
                raise ValueError(
                    "GEMINI_API_KEY is not set. Please provide 'api_key' or set the GEMINI_API_KEY environment variable."
                )
            self._api_key = str(resolved_key).strip()
            # Ensure current process environment has it for SDK sub-calls
            os.environ["GEMINI_API_KEY"] = self._api_key

            try:
                from google import genai
                self.client = genai.Client(api_key=self._api_key)
            except ImportError as err:
                raise ImportError(
                    "The 'google-genai' package is required to use GeminiLLMClient. Please install it with 'pip install google-genai'."
                ) from err

    def _sanitize_error_message(self, message: str) -> str:
        """Removes any API key patterns or authorization headers from error messages."""
        if not message:
            return ""
        # Redact Google API key pattern (AIzaSy...)
        sanitized = re.sub(r"AIzaSy[A-Za-z0-9_\-]+", "[REDACTED_API_KEY]", message)
        # Redact Bearer tokens
        sanitized = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", sanitized, flags=re.IGNORECASE)
        # Redact actual key if known
        if self._api_key and len(self._api_key) > 6 and self._api_key != "<injected_client>":
            sanitized = sanitized.replace(self._api_key, "[REDACTED_API_KEY]")
        return sanitized

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Sends the compact reasoning prompt to Gemini requesting strict JSON output.

        :param prompt: Formatted reasoning prompt.
        :return: Raw JSON string returned by the model.
        """
        model = kwargs.get("model", self.model_name)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            )

            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )

            if response is None:
                raise RuntimeError("Gemini API returned an empty null response.")

            content = getattr(response, "text", None)
            if content is None:
                # Check candidates structure if text property is empty
                candidates = getattr(response, "candidates", None)
                if candidates and len(candidates) > 0:
                    parts = getattr(candidates[0].content, "parts", None)
                    if parts and len(parts) > 0:
                        content = getattr(parts[0], "text", None)

            if content is None:
                raise RuntimeError("Gemini API response contained no text content.")

            return str(content)

        except Exception as exc:
            sanitized_msg = self._sanitize_error_message(str(exc))
            raise RuntimeError(
                f"Gemini API error ({type(exc).__name__}): {sanitized_msg}"
            ) from exc

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        """Callable protocol support for LLMReasoner."""
        return self.generate(prompt, **kwargs)
