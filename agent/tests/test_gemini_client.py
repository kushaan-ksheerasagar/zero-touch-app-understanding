"""
Offline unit tests for GeminiLLMClient using mocked google-genai client.

Validates:
- API key resolution from GEMINI_API_KEY environment variable
- Missing API key error handling
- Prompt dispatch to models.generate_content with JSON response_mime_type
- Model configurability
- JSON output retrieval
- Exception handling and secret redaction
- Compatibility with LLMReasoner
- Non-interference with GroqLLMClient and FakeLLMClient
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from agent.gemini_client import DEFAULT_GEMINI_MODEL, GeminiLLMClient
from agent.groq_client import GroqLLMClient
from agent.llm_reasoner import FakeLLMClient, LLMReasoner
from agent.reasoning import ReasoningContext
from agent.semantic import ElementRole, ScreenType
from agent.types import AgentAction


class TestGeminiLLMClient(unittest.TestCase):
    """Unit tests for GeminiLLMClient using offline mocks."""

    def setUp(self) -> None:
        self.sample_context = ReasoningContext(
            screen_id="settings_screen",
            screen_type=ScreenType.SETTINGS,
            likely_purpose="Configure settings",
            current_activity="com.android.settings.SettingsActivity",
            elements=[
                {
                    "element_id": "com.android.settings:id/network",
                    "role": ElementRole.BUTTON,
                    "label": "Network & internet",
                    "interaction": "tap",
                    "clickable": True,
                    "scrollable": False,
                    "enabled": True,
                    "explored": False,
                },
            ],
            explored_element_ids=[],
            available_interactions=[
                {
                    "element_id": "com.android.settings:id/network",
                    "role": ElementRole.BUTTON,
                    "label": "Network & internet",
                    "interaction": "tap",
                }
            ],
            recent_actions=[],
            recent_screens=[],
            exploration_step=1,
        )

    # Test A: API key is obtained from environment
    def test_a_api_key_obtained_from_environment(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSy_mock_gemini_key_12345"}):
            with patch("google.genai.Client") as mock_client_cls:
                client = GeminiLLMClient()
                self.assertEqual(client._api_key, "AIzaSy_mock_gemini_key_12345")
                mock_client_cls.assert_called_once_with(api_key="AIzaSy_mock_gemini_key_12345")

    # Test B: Missing API key produces a clear error
    def test_b_missing_api_key_raises_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_API_KEY", None)
            with patch("agent.gemini_client.resolve_gemini_api_key", return_value=None):
                with self.assertRaises(ValueError) as ctx:
                    GeminiLLMClient()
                self.assertIn("GEMINI_API_KEY", str(ctx.exception))
                self.assertIn("not set", str(ctx.exception))

    # Test C: Prompt is sent correctly to models.generate_content
    def test_c_prompt_sent_correctly(self) -> None:
        mock_raw_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"action": "tap", "target": {"element_id": "com.android.settings:id/network"}, "reason": "explore network"}'
        mock_raw_client.models.generate_content.return_value = mock_response

        client = GeminiLLMClient(client=mock_raw_client)
        test_prompt = "You are an autonomous explorer. Select next action."
        response = client.generate(test_prompt)

        mock_raw_client.models.generate_content.assert_called_once()
        call_kwargs = mock_raw_client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs["contents"], test_prompt)
        self.assertEqual(call_kwargs["config"].response_mime_type, "application/json")
        self.assertIn("action", response)

    # Test D: Model name is passed correctly
    def test_d_model_name_passed_correctly(self) -> None:
        mock_raw_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"action": "back"}'
        mock_raw_client.models.generate_content.return_value = mock_response

        custom_model = "gemini-2.0-flash"
        client = GeminiLLMClient(client=mock_raw_client, model_name=custom_model)
        client.generate("prompt")

        call_kwargs = mock_raw_client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs["model"], custom_model)

    # Test E: JSON response is returned correctly
    def test_e_json_response_returned_correctly(self) -> None:
        mock_raw_client = MagicMock()
        expected_json = '{"action": "tap", "target": {"element_id": "com.android.settings:id/network"}, "reason": "explore"}'
        mock_response = MagicMock()
        mock_response.text = expected_json
        mock_raw_client.models.generate_content.return_value = mock_response

        client = GeminiLLMClient(client=mock_raw_client)
        result = client.generate("test prompt")
        self.assertEqual(result, expected_json)

    # Test F: API exceptions are handled appropriately
    def test_f_api_exceptions_handled(self) -> None:
        mock_raw_client = MagicMock()
        mock_raw_client.models.generate_content.side_effect = ConnectionError("Gemini service unreachable")

        client = GeminiLLMClient(client=mock_raw_client)
        with self.assertRaises(RuntimeError) as ctx:
            client.generate("test prompt")

        self.assertIn("Gemini API error", str(ctx.exception))
        self.assertIn("ConnectionError", str(ctx.exception))

    # Test G: No secret is printed or included in error messages
    def test_g_no_secret_leaked_in_errors(self) -> None:
        mock_raw_client = MagicMock()
        secret_key = "AIzaSy_super_secret_token_1234567890"
        mock_raw_client.models.generate_content.side_effect = Exception(
            f"Authentication failure using {secret_key} with header Bearer {secret_key}"
        )

        client = GeminiLLMClient(api_key=secret_key, client=mock_raw_client)
        with self.assertRaises(RuntimeError) as ctx:
            client.generate("test prompt")

        err_str = str(ctx.exception)
        self.assertNotIn(secret_key, err_str)
        self.assertIn("[REDACTED_API_KEY]", err_str)

    # Test H: GeminiLLMClient works with existing LLMReasoner interface
    def test_h_gemini_client_integration_with_llm_reasoner(self) -> None:
        mock_raw_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"action": "tap", "target": {"element_id": "com.android.settings:id/network"}, "reason": "Configuring network"}'
        mock_raw_client.models.generate_content.return_value = mock_response

        gemini_client = GeminiLLMClient(client=mock_raw_client)
        reasoner = LLMReasoner(client=gemini_client)

        action = reasoner.decide(self.sample_context)

        self.assertIsInstance(action, AgentAction)
        self.assertEqual(action.action, "tap")
        self.assertEqual(action.target.element_id, "com.android.settings:id/network")
        self.assertEqual(action.reason, "Configuring network")

        # Test failure fallback: If Gemini raises an exception, LLMReasoner falls back safely to 'back'
        mock_raw_client.models.generate_content.side_effect = TimeoutError("Request timed out")
        fallback_action = reasoner.decide(self.sample_context)
        self.assertEqual(fallback_action.action, "back")
        self.assertIn("model client error", fallback_action.reason)

    # Test I: Non-interference with Groq and FakeLLMClient
    def test_i_coexistence_with_groq_and_fake(self) -> None:
        fake_client = FakeLLMClient({
            "action": "tap",
            "target": {"element_id": "com.android.settings:id/network"},
            "reason": "fake offline decision",
        })
        reasoner = LLMReasoner(client=fake_client)
        action = reasoner.decide(self.sample_context)

        self.assertEqual(action.action, "tap")
        self.assertEqual(action.target.element_id, "com.android.settings:id/network")

        # Confirm GroqLLMClient is still importable and valid
        self.assertIsNotNone(GroqLLMClient)


if __name__ == "__main__":
    unittest.main()
