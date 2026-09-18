# NRG Grid API

FastAPI backend with a root endpoint and a health check.

## Setup

Run from `backend/` using Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Development

```bash
fastapi dev app/main.py
```

The API runs at http://127.0.0.1:8000. Interactive API documentation is
available at `/docs` and `/redoc`; the health check is at `/health`.

## Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
