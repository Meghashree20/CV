# Skin Analysis API

Phase 1 backend foundation for the personalized skin analysis service. This package serves a health check, loads configuration from the environment, and reports whether MongoDB is reachable. It does not authenticate users, accept images, or run a model.

The Colab scripts in `Data/` are unchanged. ACNE04 is academic-use-only and is not downloaded or used here.

## Layout

```
backend/
  app/
    main.py              Application factory
    core/                Settings, logging, errors
    api/routes/          HTTP routes
    schemas/             Pydantic response models
    db/                  Motor client
    repositories/        Reserved for later persistence
    services/            Health report
  tests/
  .env.example
  requirements.txt
```

Image bytes and model weights are out of scope. Do not commit `.env`, `.pt`, `.onnx`, or `.pth` files.

## Setup

Requires Python 3.13 and a MongoDB instance if you want `/health` to report `connected`. The process still starts when MongoDB is down; `/health` then returns `status: degraded`.

From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` if MongoDB is not on `localhost:27017`. Use a `mongodb://` or `mongodb+srv://` URI. Do not put that URI in source code.

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: `http://127.0.0.1:8000/health`
- OpenAPI: `http://127.0.0.1:8000/docs`

Allowed browser origins default to `http://localhost:3000` and `http://localhost:5173`. Change `CORS_ORIGINS` in `.env` for another React host. Separate origins with commas.

## Health response

`GET /health` always answers from the API process.

| Field | Meaning |
|---|---|
| `status` | `ok` when MongoDB answers a ping, otherwise `degraded` |
| `api` | `ok` when this process handled the request |
| `mongodb` | `connected` or `unavailable` |
| `environment` | Value of `ENVIRONMENT` |
| `service` | Value of `APP_NAME` |

HTTP status stays 200 in both cases so a missing database does not look like a crashed API.

## Tests

```powershell
pytest
```

MongoDB unit tests use fakes. The health test calls a real ping with a short timeout, so it passes whether or not MongoDB is running.

## Environment

| Variable | Purpose |
|---|---|
| `APP_NAME` | Service name returned by `/health` |
| `ENVIRONMENT` | Named environment, such as `development` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |
| `MONGODB_URI` | Connection string |
| `MONGODB_DB_NAME` | Database name selected after a successful ping |
| `MONGODB_SERVER_SELECTION_TIMEOUT_MS` | How long a ping waits |
| `CORS_ORIGINS` | Comma-separated React origins |
