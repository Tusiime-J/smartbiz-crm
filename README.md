# SmartBiz CRM — Flask + PostgreSQL MVP

This deployment-ready version uses PostgreSQL through the `DATABASE_URL` environment variable. It creates the `customers`, `sales`, and `followups` tables automatically when the application starts and a database URL is configured.

## Features
- Customer records: add, list, edit, search and delete
- Sales opportunities and pipeline stages
- Follow-up tasks: create, view, complete/reopen and delete
- Dashboard and sales reports (UGX)
- Responsive interface

## Render deployment
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variable `DATABASE_URL`: Render PostgreSQL **Internal Database URL**
- Environment variable `SMARTBIZ_SECRET_KEY`: a long random secret value

The repository root must contain `app.py`, `requirements.txt`, `templates/`, and `static/`.

## Local development
Set `DATABASE_URL` to a PostgreSQL connection URL, then run:

```bash
pip install -r requirements.txt
python app.py
```

## Important
This is an academic MVP. It does not yet include login, roles, CSRF protection, or production-grade access controls. Use fictional test data until those protections are implemented. A free Render PostgreSQL database expires after its free period; upgrade or migrate before expiry to retain data long-term.
