from __future__ import annotations

from trading_engine.ai import MockAIProvider


def test_mock_ai_provider_is_advisory_only() -> None:
    provider = MockAIProvider()

    assert "BUY" in provider.explain_signal({"signal_type": "BUY", "reason": "test"})
    assert "Risk manager blocked" in provider.explain_risk_block({"triggered_rules": ["spread"]})
    assert "1 open positions" in provider.summarize_positions([{"symbol": "EURUSD"}])
