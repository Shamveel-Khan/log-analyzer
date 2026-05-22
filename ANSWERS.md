# Answers

## How to run

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

Open the Vite URL (default http://localhost:5173) and upload a log file.

## Stack choice

I chose Python + FastAPI for the backend because it keeps log parsing close to the analyzer, runs locally with minimal ceremony, and is easy to extend with streaming uploads. React + Vite was selected for a fast, clean UI with charting. A worse choice would be a heavier backend framework or a full database-backed stack, which would slow iteration and add complexity for a single-file upload workflow.

## One real edge case

When `--since` is provided and a line has no timestamp, the analyzer increments `since_missing_timestamp` and skips that line. See [src/analyze.py](src/analyze.py#L384-L389). Without this handling, the comparison against a missing timestamp would raise a `TypeError`, aborting the run and losing results.

## AI usage

- GitHub Copilot: asked it to draft parts of the FastAPI upload endpoint and JSON response wiring. I changed the output by adding the shared `build_json_report` schema and API response structure, and refined the endpoint behavior to match the analyzer output and UI needs.
- GitHub Copilot: used for some UI scaffolding, then I adjusted styles, added the dark/light toggle, and tuned the layout for the analytics panels.

## Honest gap

Percentiles are computed in-memory using full duration lists, which can be heavy for very large logs. With another day, I would switch to streaming quantile sketches (t-digest or reservoir sampling) to keep memory bounded while preserving accurate p50/p95/p99 estimates.