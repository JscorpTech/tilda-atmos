# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **payment gateway integration service** that bridges [Tilda](https://tildapublishing.com/) e-commerce with the [Atmos](https://atmos.uz/) payment processor (Uzbekistan). It is a lean FastAPI application deployed on Kubernetes.

## Running the Service

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (requires .env or exported env vars)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Build Docker image
docker build -t atmos-fastapi .

# Run with Docker
docker run --env-file .env -p 8000:8000 atmos-fastapi
```

There are no automated tests. Validation is done via manual integration with the Atmos sandbox and Tilda test orders.

## Required Environment Variables

See `config.py` for all vars. The critical ones:

| Variable | Description |
|---|---|
| `ATMOS_CONSUMER_KEY` | Atmos OAuth2 client ID |
| `ATMOS_CONSUMER_SECRET` | Atmos OAuth2 client secret |
| `ATMOS_STORE_ID` | Atmos merchant store ID (default: 100265) |
| `ATMOS_API_URL` | Atmos gateway base URL |
| `DEBUG_MODE` | When `true`, forces all payments to 1000 UZS |
| `FINAL_REDIRECT_URL` | Post-payment redirect (default: https://ventureforum.asia/) |
| `DB_FILE` | SQLite path (default: `DATABASE.sqlite`) |

Copy `k8s/secret.yaml.example` to `k8s/secret.yaml` for Kubernetes secret configuration.

## Architecture

**Entry points (`main.py`):**
- `POST /` — Receives form data from Tilda, obtains Atmos token, creates invoice, saves order to SQLite, redirects user to Atmos payment page.
- `POST /callback.php` — Webhook from Atmos after payment. Looks up the order, notifies Tilda's callback URL, marks order as paid, and returns `{"status": 1}`. **Atmos only finalizes payment if this returns `{"status": 1}`** — do not break this response.
- `GET /` — Health check.

**Key modules:**
- `atmos_client.py` — Atmos API integration: OAuth2 token acquisition, invoice creation.
- `database.py` — SQLite layer with WAL mode. Three tables: `orders`, `rate_cache` (1h TTL), `token_cache`.
- `config.py` — All configuration from environment variables.
- `logger.py` — Dual-stream logging (stdout + file).

**Payment flow:**
1. Tilda POSTs an order (amount in KZT) with an MD5 hash for verification.
2. The app validates the hash, converts currency to UZS (with exchange rate caching), converts to tiyin (× 100).
3. Creates an Atmos invoice and stores the order in SQLite.
4. Redirects the user to the Atmos-hosted payment page.
5. Atmos calls `/callback.php` on completion; the app notifies Tilda and marks the order paid.

## Deployment

**CI/CD:** GitHub Actions (`docker-push.yml`) triggers on git tag push, builds and pushes to `registry.jscorp.uz`.

**Kubernetes:** Two deployment variants:
- `k8s/` — primary (namespace: `ventureforum`, ingress: `atmos.jscorp.uz`)
- `k8s-mostinvest/` — alternate tenant (namespace: `mostinvest`)

Persistent volume is mounted at `/data` for the SQLite database and log files.
