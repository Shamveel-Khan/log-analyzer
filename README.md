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

## Notes

- The analyzer is designed to never crash on malformed lines.
- It reports how many lines were malformed, blank, or missing key fields.
- It counts anomalies instead of silently dropping data.
