from __future__ import annotations

import json
import os
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from trading_engine.configuration import LiveTradingSettings

SYSTEM_PROMPT = (
    "You are an educational trading-analysis assistant. You may explain signals, "
    "risk decisions, positions, trades, and backtests. You must not give financial "
    "advice, promise profit, approve trades, place orders, close positions, modify "
    "broker settings, or override the risk manager."
)


class AIProvider(ABC):
    @abstractmethod
    def explain_signal(self, signal: dict[str, Any]) -> str: ...

    @abstractmethod
    def explain_risk_block(self, risk_decision: dict[str, Any]) -> str: ...

    @abstractmethod
    def summarize_positions(self, positions: list[dict[str, Any]]) -> str: ...

    @abstractmethod
    def review_trade(self, trade: dict[str, Any]) -> str: ...

    @abstractmethod
    def review_backtest(self, metrics: dict[str, Any]) -> str: ...


class MockAIProvider(AIProvider):
    """Local deterministic provider. It never approves, places, or closes trades."""

    def explain_signal(self, signal: dict[str, Any]) -> str:
        signal_type = signal.get("signal_type", "HOLD")
        reason = signal.get("reason", "")
        return f"Signal explanation: {signal_type} because {reason}."

    def explain_risk_block(self, risk_decision: dict[str, Any]) -> str:
        rules = ", ".join(risk_decision.get("triggered_rules", []))
        return f"Risk manager blocked the trade. Triggered rules: {rules}."

    def summarize_positions(self, positions: list[dict[str, Any]]) -> str:
        return f"There are {len(positions)} open positions to review."

    def review_trade(self, trade: dict[str, Any]) -> str:
        return "Trade review: check whether the setup followed the plan and respected risk."

    def review_backtest(self, metrics: dict[str, Any]) -> str:
        return (
            "Backtest review: inspect return, drawdown, trade count, and whether assumptions "
            "match realistic execution."
        )


@dataclass(frozen=True, slots=True)
class LocalOllamaProvider(AIProvider):
    base_url: str
    model: str

    def explain_signal(self, signal: dict[str, Any]) -> str:
        return self._generate(
            f"Explain this trading signal without giving financial advice: {signal}"
        )

    def explain_risk_block(self, risk_decision: dict[str, Any]) -> str:
        return self._generate(f"Explain why this risk decision blocked a trade: {risk_decision}")

    def summarize_positions(self, positions: list[dict[str, Any]]) -> str:
        return self._generate(f"Summarize these positions without recommending trades: {positions}")

    def review_trade(self, trade: dict[str, Any]) -> str:
        return self._generate(f"Review this trade outcome educationally: {trade}")

    def review_backtest(self, metrics: dict[str, Any]) -> str:
        return self._generate(f"Review these backtest metrics educationally: {metrics}")

    def _generate(self, prompt: str) -> str:
        if not self.model:
            return "Ollama model is not configured."
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"}:
            return "Ollama base URL must use http or https."
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode()
        request = urllib.request.Request(  # noqa: S310
            f"{self.base_url.rstrip('/')}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload.get("response", ""))


@dataclass(frozen=True, slots=True)
class OpenAIProvider(AIProvider):
    api_key: str
    model: str
    base_url: str = ""
    timeout_seconds: int = 30
    client_factory: Callable[..., Any] | None = None

    def explain_signal(self, signal: dict[str, Any]) -> str:
        return self._generate(
            f"Explain this trading signal without giving financial advice: {signal}"
        )

    def explain_risk_block(self, risk_decision: dict[str, Any]) -> str:
        return self._generate(f"Explain why this risk rule blocked a trade: {risk_decision}")

    def summarize_positions(self, positions: list[dict[str, Any]]) -> str:
        return self._generate(
            f"Summarize these open positions without recommending trades: {positions}"
        )

    def review_trade(self, trade: dict[str, Any]) -> str:
        return self._generate(f"Review this trade outcome educationally: {trade}")

    def review_backtest(self, metrics: dict[str, Any]) -> str:
        return self._generate(f"Review these backtest metrics educationally: {metrics}")

    def _generate(self, prompt: str) -> str:
        if not self.api_key:
            return "OpenAI API key is not configured."
        if not self.model:
            return "OpenAI model is not configured."

        try:
            client = self._client()
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
        except ImportError:
            return "OpenAI SDK is not installed. Install with `pip install -e .[openai]`."
        except Exception as exc:
            return f"OpenAI request failed: {exc}"

        output_text = getattr(response, "output_text", "")
        if output_text:
            return str(output_text)
        return _extract_response_text(response)

    def _client(self) -> Any:
        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout_seconds,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        if self.client_factory is not None:
            return self.client_factory(**kwargs)

        from openai import OpenAI

        return OpenAI(**kwargs)


def get_ai_provider(settings: LiveTradingSettings | None = None) -> AIProvider:
    live_settings = settings or LiveTradingSettings.from_env()
    if live_settings.ai_provider == "openai":
        return OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=live_settings.openai_model,
            base_url=live_settings.openai_base_url,
            timeout_seconds=live_settings.openai_timeout_seconds,
        )
    if live_settings.ai_provider == "ollama":
        return LocalOllamaProvider(
            base_url=live_settings.ollama_base_url,
            model=live_settings.ollama_model,
        )
    return MockAIProvider()


def _extract_response_text(response: Any) -> str:
    output = getattr(response, "output", None)
    if not output:
        return ""
    parts: list[str] = []
    for item in output:
        content = getattr(item, "content", [])
        for content_item in content:
            text = getattr(content_item, "text", "")
            if text:
                parts.append(str(text))
    return "\n".join(parts)
