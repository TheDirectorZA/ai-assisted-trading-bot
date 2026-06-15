from __future__ import annotations


class BrokerError(RuntimeError):
    """Base broker exception."""


class BrokerConnectionError(BrokerError):
    """Raised when a broker cannot connect or is disconnected."""


class BrokerCredentialsError(BrokerError):
    """Raised when required broker credentials are missing or invalid."""


class BrokerOrderError(BrokerError):
    """Raised when an order request is rejected or cannot be sent."""


class BrokerSymbolError(BrokerError):
    """Raised when a symbol is missing, hidden, or not tradeable."""
