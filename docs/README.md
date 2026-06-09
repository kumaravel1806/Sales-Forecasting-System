# Retail Operations and Forecasting Platform

## Overview
A full-stack, mobile-first PWA for retail operations with a Flask API. This Step 1 scaffold includes:
- Minimal Flask API with JWT/auth stub and modular blueprints.
- Frontend static site (Tailwind via CDN) with PWA manifest + service worker.
- Docker and docker-compose for local dev (api, web, worker services).
- Consistent JSON envelope: `{ success: bool, data: ..., meta: ... }`.

## Structure
- frontend/: Static PWA, NGINX config, dev preview page.
- backend/: Flask app, blueprints, Dockerfile, requirements.
- ml/: Placeholder for scripts and notebooks.
- docs/: This README, more docs in later steps.
- tests/: Basic smoke test to be added next.

## Run locally (Docker)
1. Copy `.env.example` to `.env` and adjust values.
2. Run: `docker compose up --build`
3. Open http://localhost:5173 to view the frontend.
4. API available at http://localhost:8000/api/health (also proxied via NGINX `/api/`).

## Local vs Cloud
- Local mode uses SQLite and lightweight API; ML deps are deferred to later steps to keep the footprint small.
- Cloud mode will add heavier ML dependencies and remote training scripts.

## Notes on hardware
- Optimized for a modest CPU machine. Using CDN Tailwind avoids a Node build step.
- Gunicorn workers set to 2 by default; adjust based on cores.

## Progress and Features

- Step 1: Scaffold complete.
- Step 2: CSV/Excel upload + cleaning endpoint/UI.
  - POST `/api/admin/upload` (multipart): returns before/after summary and saves cleaned CSV.
  - UI: `/admin.html`.
- Step 3: Sales forecast baseline (LinearRegression time-index).
  - POST `/api/ml/predict/sales` accepts JSON or file; returns per-SKU forecasts.
- Step 4: Model comparison (LR vs XGB) + script stubs.
  - POST `/api/ml/compare` returns MAE/RMSE/ MAPE per SKU and overall averages.
  - UI: `/compare.html`.
- Step 5: LSTM training script (local vs cloud), configs and remote helper.
  - `python -m backend.ml.train_lstm --input data.csv --config ml/config.local.yaml`
  - `ml/remote_train.sh` for cloud GPU.
- Step 6: Inventory/FEFO + notifications.
  - Tables: products, inventory_batches.
  - Endpoints: `/api/inventory/products`, `/api/inventory/batches`, `/api/inventory/fefo_picklist`, `/api/inventory/near_expiry`, `/api/inventory/dispatch`, `/api/inventory/notify`.
  - UI: `/inventory.html`.
- Step 7: Reviews, Q&A, sentiment baseline (TFIDF+LogReg).
  - Endpoints: `/api/reviews/submit`, `/api/reviews/list`, `/api/qa/ask`, `/api/qa/answer`, `/api/qa/list`, `/api/ml/predict/sentiment`.
  - UI: `/product.html`.
- Step 8: Assistant (Gemini) placeholder.
  - Endpoint: `/api/assistant/chat`.
  - UI: `/assistant.html`.

## Assistant Configuration (Gemini)
- Set environment variables in `.env`:
  - `GEMINI_API_KEY=...`
  - `GEMINI_MODEL=gemini-2.0-pro` (default)
- The assistant endpoint will return a helpful message if not configured.

## Tests
- Install local deps: `python -m pip install -r backend/requirements.txt && python -m pip install pytest`
- Run: `pytest -q`
- Included tests:
  - `tests/test_smoke.py`: API health
  - `tests/test_admin_upload.py`: CSV cleaning
  - `tests/test_predict_sales.py`: forecast JSON path
  - `tests/test_reviews_and_sentiment.py`: reviews + sentiment

## Architecture (ASCII)

```
[Frontend (PWA)] --NGINX--> /api/* --> [Flask API]
  | admin.html -> /api/admin/upload
  | compare.html -> /api/ml/compare
  | inventory.html -> /api/inventory/*
  | product.html -> /api/reviews/*, /api/qa/*
  | assistant.html -> /api/assistant/chat (Gemini)

[Flask Blueprints]
  auth, products, orders, analytics, ml, admin, inventory, reviews, qa, assistant

[SQLite DB]
  products, inventory_batches, reviews, qa

[ML]
  simple_forecast (LR), xgb_forecast (optional), metrics, sentiment, train_lstm
```
