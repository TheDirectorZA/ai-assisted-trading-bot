from __future__ import annotations

from trading_engine.brokers.mock_broker import MockBroker


class PaperBroker(MockBroker):
    """Safe paper-trading broker with the same interface as a live broker."""
