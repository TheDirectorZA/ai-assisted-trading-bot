# AI Assistant

The AI assistant cannot trade.

Allowed:

- explain signals
- explain risk blocks
- summarize open positions
- summarize recent trades
- generate trade journal notes
- review backtest results
- review trade outcomes

Not allowed:

- approve trades
- place orders
- close positions
- change live settings
- modify broker credentials
- override the risk manager
- promise profit

The default provider is `MockAIProvider`. `LocalOllamaProvider` is optional and
uses a local Ollama-compatible API.
