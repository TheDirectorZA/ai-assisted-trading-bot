# Deployment

The deployment target is local-first:

- Django development server
- FastAPI Uvicorn service
- Celery worker
- Celery beat
- Redis
- SQLite for simple local use
- Optional PostgreSQL through Docker Compose profile

Run Compose:

```bash
docker-compose up --build
```

For live MT5 execution, prefer running the broker worker on the host machine
where the MT5 terminal is installed and logged in. Production-like deployments
should use PostgreSQL, supervised processes, backups, log retention, and strict
environment-specific settings.
