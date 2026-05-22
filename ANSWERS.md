# Answers

## How to run

1. Install Python 3.10+.
2. (Optional) Generate a sample log:

```bash
python scripts/generate_log.py --lines 2000 --output sample.log
```

3. Run the analyzer:

```bash
python src/cli.py sample.log --format both
```

No third-party packages are required.

## Stack choice

I chose Python for fast iteration on text parsing, excellent standard library support (datetime, json, shlex), and portability across machines. A worse choice here would be a heavy web framework stack (e.g., a full React/Node app) because it adds setup and complexity without improving robustness for plain-text log parsing.

## One real edge case

When `--since` is provided and a line has no timestamp, the analyzer increments `since_missing_timestamp` and skips that line instead of crashing or mis-filtering. See [src/analyze.py](src/analyze.py#L332-L335). Without this handling, comparing `None` to a datetime would raise a `TypeError`, aborting the run and losing all results.

## AI usage

## Honest gap

Percentiles are computed in-memory using full duration lists, which can be heavy for very large logs. With more time, I would switch to streaming quantile sketches (t-digest or reservoir sampling) to keep memory bounded while preserving accurate p50/p95/p99 estimates.

## Update

The analyzer now emits per-endpoint latency percentiles (p50/p95/p99), time-bucketed error rates, and endpoint summaries that feed a local FastAPI server. The Vite + React frontend uploads a log file and renders status distribution, error rate over time, top IPs, slow endpoints, and anomaly counts based on the JSON schema returned by `POST /analyze`.
