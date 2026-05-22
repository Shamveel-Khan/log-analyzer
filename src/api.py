from __future__ import annotations

import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from analyze import analyze_log, build_json_report, parse_timestamp

app = FastAPI(title="Log Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_log_file(
    file: UploadFile = File(...),
    bucket_seconds: int = Query(60, ge=10, le=3600),
    top_n: int = Query(10, ge=1, le=100),
    since: Optional[str] = Query(None),
) -> dict:
    since_dt = None
    if since:
        since_dt = parse_timestamp(since)
        if since_dt is None:
            raise HTTPException(status_code=400, detail="invalid_since")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)

        stats = analyze_log(tmp_path, since=since_dt, bucket_seconds=bucket_seconds)
        return build_json_report(stats, top_n=top_n)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "Missing uvicorn. Install with: pip install fastapi uvicorn"
        ) from exc

    uvicorn.run(app, host="127.0.0.1", port=8000)
