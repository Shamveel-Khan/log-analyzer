# Log Analyzer

A resilient CLI that scans mixed-format server logs, tolerates malformed lines, and produces a clear report plus optional JSON output.

## Requirements

- Python 3.10+

## Generate sample logs

```bash
python scripts/generate_log.py --lines 2000 --output sample.log
```

## Analyze logs

```bash
python src/cli.py sample.log
```

JSON output:

```bash
python src/cli.py sample.log --format json
```

Filter by time (best-effort parse of multiple formats):

```bash
python src/cli.py sample.log --since "2024-03-15T14:30:00Z"
```

## Local web app

The web UI uploads a log file to a local API and renders charts for the analytics.

### API server (FastAPI)

Install dependencies:

```bash
pip install fastapi uvicorn
```

Run the API:

```bash
python src/api.py
```

The server listens on http://127.0.0.1:8000 and exposes `POST /analyze`.

### Frontend (Vite + React)

```bash
cd web
npm install
npm run dev
```

Open the URL printed by Vite (default http://localhost:5173).

### Generate a sample log

```bash
python scripts/generate_log.py --lines 2000 --output sample.log
```

## Notes

- The analyzer is designed to never crash on malformed lines.
- It reports how many lines were malformed, blank, or missing key fields.
- It counts anomalies instead of silently dropping data.
