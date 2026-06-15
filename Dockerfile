FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=ai_live_trading_bot.settings \
    TRADING_MODE=paper \
    LIVE_TRADING_ENABLED=false \
    LIVE_TRADING_ARMED=false

WORKDIR /app

RUN addgroup --system app && \
    adduser --system --ingroup app app && \
    mkdir -p /app /data && \
    chown -R app:app /app /data

COPY pyproject.toml README.md ./
COPY ai_live_trading_bot ./ai_live_trading_bot
COPY fastapi_app ./fastapi_app
COPY trading_engine ./trading_engine
COPY manage.py ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

USER app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
