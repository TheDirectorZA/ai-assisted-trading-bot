from __future__ import annotations

from trading_engine.ai import MockAIProvider, OpenAIProvider, get_ai_provider


def test_mock_ai_provider_is_advisory_only() -> None:
    provider = MockAIProvider()

    assert "BUY" in provider.explain_signal({"signal_type": "BUY", "reason": "test"})
    assert "Risk manager blocked" in provider.explain_risk_block({"triggered_rules": ["spread"]})
    assert "1 open positions" in provider.summarize_positions([{"symbol": "EURUSD"}])


def test_openai_provider_uses_responses_api_with_fake_client() -> None:
    provider = OpenAIProvider(
        api_key="test-key",
        model="gpt-test",
        client_factory=FakeOpenAIClient,
    )

    assert provider.explain_signal({"signal_type": "BUY"}) == "openai explanation"


def test_openai_provider_selected_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    provider = get_ai_provider()

    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-test"


class FakeOpenAIClient:
    def __init__(self, **kwargs):
        self.responses = FakeResponses()


class FakeResponses:
    def create(self, **kwargs):
        return FakeResponse()


class FakeResponse:
    output_text = "openai explanation"
