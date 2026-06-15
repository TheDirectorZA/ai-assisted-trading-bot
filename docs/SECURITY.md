# Security

- `.env` is ignored by Git.
- Broker credentials are read from environment variables.
- Passwords are never rendered by the API or dashboard.
- Django CSRF protection is enabled.
- Live trading is disabled by default.
- Admin-only controls should be used for production deployments.
- Risk decisions and dangerous actions are audited.
- Docker Compose does not include secrets.
