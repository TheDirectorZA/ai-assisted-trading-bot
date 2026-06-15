from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

CONFIRMATION_PHRASE = "I_UNDERSTAND_REAL_MONEY_IS_AT_RISK"
REAL_ORDER_CONFIRMATION_PHRASE = "I_UNDERSTAND_THIS_PLACES_A_REAL_TRADE"


class TradingMode(StrEnum):
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class MT5Credentials:
    login: int | None
    password: str
    server: str
    terminal_path: Path | None
    timeout_ms: int
    magic_number: int
    default_deviation_points: int

    @classmethod
    def from_env(cls) -> MT5Credentials:
        raw_login = os.getenv("MT5_LOGIN", "").strip()
        return cls(
            login=int(raw_login) if raw_login.isdigit() else None,
            password=os.getenv("MT5_PASSWORD", ""),
            server=os.getenv("MT5_SERVER", ""),
            terminal_path=_optional_path(os.getenv("MT5_TERMINAL_PATH")),
            timeout_ms=_int_env("MT5_TIMEOUT_MS", 60000),
            magic_number=_int_env("MT5_MAGIC_NUMBER", 20260615),
            default_deviation_points=_int_env("MT5_DEFAULT_DEVIATION_POINTS", 20),
        )

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if self.login is None:
            missing.append("MT5_LOGIN")
        if not self.password:
            missing.append("MT5_PASSWORD")
        if not self.server:
            missing.append("MT5_SERVER")
        return missing


@dataclass(frozen=True, slots=True)
class LiveTradingSettings:
    mode: TradingMode
    live_trading_enabled: bool
    live_trading_armed: bool
    confirmation_phrase: str
    max_tick_age_seconds: int
    max_candle_age_seconds: int
    max_order_failures: int
    close_positions_on_kill_switch: bool
    ai_provider: str
    ollama_base_url: str
    ollama_model: str
    openai_model: str = "gpt-5.4-mini"
    openai_base_url: str = ""
    openai_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> LiveTradingSettings:
        raw_mode = os.getenv("TRADING_MODE", "paper").strip().lower()
        mode = (
            TradingMode(raw_mode)
            if raw_mode in {item.value for item in TradingMode}
            else TradingMode.PAPER
        )
        return cls(
            mode=mode,
            live_trading_enabled=_bool_env("LIVE_TRADING_ENABLED", False),
            live_trading_armed=_bool_env("LIVE_TRADING_ARMED", False),
            confirmation_phrase=os.getenv("LIVE_CONFIRMATION_PHRASE", ""),
            max_tick_age_seconds=_int_env("MAX_TICK_AGE_SECONDS", 10),
            max_candle_age_seconds=_int_env("MAX_CANDLE_AGE_SECONDS", 120),
            max_order_failures=_int_env("MAX_ORDER_FAILURES", 3),
            close_positions_on_kill_switch=_bool_env("CLOSE_POSITIONS_ON_KILL_SWITCH", False),
            ai_provider=os.getenv("AI_PROVIDER", "mock").strip().lower(),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
            openai_timeout_seconds=_int_env("OPENAI_TIMEOUT_SECONDS", 30),
        )

    def activation_errors(self) -> list[str]:
        errors: list[str] = []
        if self.mode is not TradingMode.LIVE:
            errors.append("TRADING_MODE must be live")
        if not self.live_trading_enabled:
            errors.append("LIVE_TRADING_ENABLED must be true")
        if not self.live_trading_armed:
            errors.append("LIVE_TRADING_ARMED must be true")
        if self.confirmation_phrase != CONFIRMATION_PHRASE:
            errors.append("LIVE_CONFIRMATION_PHRASE is missing or incorrect")
        return errors

    def assert_live_trading_allowed(self) -> None:
        errors = self.activation_errors()
        if errors:
            raise LiveTradingNotAllowed("; ".join(errors))


class LiveTradingNotAllowed(RuntimeError):
    """Raised when live trading gates are not satisfied."""


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value)
