"""
Offline unit tests for GroqLLMClient.

Mocks the groq.Groq client completely. Zero external network calls.
Validates:
- Requirements A through I
- Environment variable credential retrieval
- Sanitization of secrets in error reporting
- Model configurability
- Compatibility with LLMReasoner
- Backward compatibility of FakeLLMClient
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from agent.groq_client import DEFAULT_GROQ_MODEL, GroqLLMClient
from agent.llm_reasoner import FakeLLMClient, LLMReasoner
from agent.reasoning import ReasoningContext
from agent.semantic import ElementRole, ScreenType
from agent.types import AgentAction


class TestGroqLLMClient(unittest.TestCase):
    """Unit tests for GroqLLMClient using mocks."""

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

    # Requirement A: API key is obtained from environment
    def test_a_api_key_obtained_from_environment(self) -> None:
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_env_test_key_12345"}):
            mock_groq_mod = MagicMock()
            with patch.dict("sys.modules", {"groq": mock_groq_mod}):
                mock_groq = mock_groq_mod.Groq
                client = GroqLLMClient()
                self.assertEqual(client._api_key, "gsk_env_test_key_12345")
                mock_groq.assert_called_once_with(
                    api_key="gsk_env_test_key_12345",
                    timeout=30.0,
                )

    # Requirement B: Missing API key produces a clear error
    def test_b_missing_api_key_raises_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            # Ensure GROQ_API_KEY is not present
            os.environ.pop("GROQ_API_KEY", None)
            with self.assertRaises(ValueError) as ctx:
                GroqLLMClient()
            self.assertIn("GROQ_API_KEY", str(ctx.exception))
            self.assertIn("not set", str(ctx.exception))

    # Requirement C: Prompt is sent correctly
    def test_c_prompt_sent_correctly(self) -> None:
        mock_raw_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"action": "tap", "target": {"element_id": "com.android.settings:id/network"}, "reason": "explore network"}'
        mock_raw_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        client = GroqLLMClient(client=mock_raw_client)
        test_prompt = "You are an autonomous explorer. Select next action."
        response = client.generate(test_prompt)

        mock_raw_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_raw_client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs["messages"], [{"role": "user", "content": test_prompt}])
        self.assertEqual(call_kwargs["response_format"], {"type": "json_object"})
        self.assertIn("action", response)

    # Requirement D: Model name is passed correctly
    def test_d_model_name_passed_correctly(self) -> None:
        mock_raw_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"action": "back"}'
        mock_raw_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        custom_model = "llama-3.1-8b-instant"
        client = GroqLLMClient(client=mock_raw_client, model_name=custom_model)
        client.generate("prompt")

        call_kwargs = mock_raw_client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], custom_model)

    # Requirement E: JSON response is returned correctly
    def test_e_json_response_returned_correctly(self) -> None:
        mock_raw_client = MagicMock()
        expected_json = '{"action": "tap", "target": {"element_id": "com.android.settings:id/network"}, "reason": "explore"}'
        mock_choice = MagicMock()
        mock_choice.message.content = expected_json
        mock_raw_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        client = GroqLLMClient(client=mock_raw_client)
        result = client.generate("test prompt")
        self.assertEqual(result, expected_json)

    # Requirement F: API exceptions are handled appropriately
    def test_f_api_exceptions_handled(self) -> None:
        mock_raw_client = MagicMock()
        mock_raw_client.chat.completions.create.side_effect = ConnectionError("Groq service unreachable")

        client = GroqLLMClient(client=mock_raw_client)
        with self.assertRaises(RuntimeError) as ctx:
            client.generate("test prompt")

        self.assertIn("Groq API error", str(ctx.exception))
        self.assertIn("ConnectionError", str(ctx.exception))

    # Requirement G: No secret is printed or included in error messages
    def test_g_no_secret_leaked_in_errors(self) -> None:
        mock_raw_client = MagicMock()
        secret_key = "gsk_super_secret_token_abcdef12345"
        mock_raw_client.chat.completions.create.side_effect = Exception(
            f"Unauthorized: Invalid key {secret_key} with header Bearer {secret_key}"
        )

        client = GroqLLMClient(api_key=secret_key, client=mock_raw_client)
        with self.assertRaises(RuntimeError) as ctx:
            client.generate("test prompt")

        err_str = str(ctx.exception)
        self.assertNotIn(secret_key, err_str)
        self.assertIn("[REDACTED_API_KEY]", err_str)

    # Requirement H: GroqLLMClient works with existing LLMReasoner interface
    def test_h_groq_client_integration_with_llm_reasoner(self) -> None:
        mock_raw_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"action": "tap", "target": {"element_id": "com.android.settings:id/network"}, "reason": "Configuring network"}'
        mock_raw_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        groq_client = GroqLLMClient(client=mock_raw_client)
        reasoner = LLMReasoner(client=groq_client)

        action = reasoner.decide(self.sample_context)

        self.assertIsInstance(action, AgentAction)
        self.assertEqual(action.action, "tap")
        self.assertEqual(action.target.element_id, "com.android.settings:id/network")
        self.assertEqual(action.reason, "Configuring network")

        # Test failure fallback: If Groq raises an exception, LLMReasoner falls back safely
        mock_raw_client.chat.completions.create.side_effect = TimeoutError("Request timed out")
        fallback_action = reasoner.decide(self.sample_context)
        self.assertEqual(fallback_action.action, "back")
        self.assertIn("model client error", fallback_action.reason)

    # Requirement I: Existing FakeLLMClient still works
    def test_i_fake_llm_client_still_works(self) -> None:
        fake_client = FakeLLMClient({
            "action": "tap",
            "target": {"element_id": "com.android.settings:id/network"},
            "reason": "fake offline decision",
        })
        reasoner = LLMReasoner(client=fake_client)
        action = reasoner.decide(self.sample_context)

        self.assertEqual(action.action, "tap")
        self.assertEqual(action.target.element_id, "com.android.settings:id/network")
        self.assertEqual(action.reason, "fake offline decision")


if __name__ == "__main__":
    unittest.main()
