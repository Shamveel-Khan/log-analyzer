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

The analyzer does not compute per-endpoint latency percentiles or “slowest endpoints,” which would be very useful in real on-call triage. With another day, I would add endpoint-level aggregation and streaming percentiles (p50/p95/p99), plus a `--top-endpoints` flag.
