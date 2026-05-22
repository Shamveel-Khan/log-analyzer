# Log Analyzer

Local log analytics with a FastAPI backend and a Vite + React frontend.

## How to run (fresh machine)

1. Install Python 3.10+ and Node.js 18+.
2. Install backend dependencies:

```bash
pip install fastapi uvicorn python-multipart
```

3. Install frontend dependencies:

```bash
cd web
npm install
```

4. (Optional) Generate a sample log:

```bash
python scripts/generate_log.py --lines 2000 --output sample.log
```

5. Start the API server:

```bash
python src/api.py
```

6. Start the frontend:

```bash
cd web
npm run dev
```

Open the URL printed by Vite (default http://localhost:5173) and upload a log file.

## CLI only (optional)

```bash
python src/cli.py sample.log
```

JSON output:

```bash
python src/cli.py sample.log --format json
```

Filter by time:

```bash
python src/cli.py sample.log --since "2024-03-15T14:30:00Z"
```
