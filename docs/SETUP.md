# Setup

Install locally:

```bash
python3 -m pip install -e ".[dev]"
cp .env.example .env
python3 manage.py migrate
python3 manage.py seed_demo
```

Run services:

```bash
make django
make fastapi
make celery-worker
make celery-beat
```

Run checks:

```bash
make test
make lint
make typecheck
```

Optional OpenAI AI provider:

```bash
python3 -m pip install -e ".[openai]"
AI_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
```
