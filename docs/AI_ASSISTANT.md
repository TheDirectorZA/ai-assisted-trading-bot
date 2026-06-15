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

The default provider is `MockAIProvider`.

Use OpenAI by installing the optional SDK and setting environment variables:

```bash
python3 -m pip install -e ".[openai]"
AI_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
```

`OpenAIProvider` uses the OpenAI Responses API through the official Python SDK.
It remains advisory only and cannot execute trades.

`LocalOllamaProvider` is optional and uses a local Ollama-compatible API.
