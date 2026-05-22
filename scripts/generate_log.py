from __future__ import annotations

import argparse
import datetime as dt
import json
import random
from typing import List

METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]
PATHS = [
    "/api/users",
    "/api/users/12",
    "/api/login",
    "/api/logout",
    "/api/orders",
    "/api/orders/42",
    "/health",
]
STATUSES = [200, 200, 200, 201, 204, 400, 401, 403, 404, 500, 502, 503]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "curl/8.1.2",
    "PostmanRuntime/7.32.0",
    "python-requests/2.31.0",
]
REFERRERS = [
    "https://example.com/app",
    "https://internal.service.local/dashboard",
    "-",
]


def random_ip() -> str:
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"


def format_standard_line(
    ts: dt.datetime, ip: str, method: str, path: str, status: int, duration_ms: int
) -> str:
    return f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')} {ip} {method} {path} {status} {duration_ms}ms"


def format_alt_timestamp(ts: dt.datetime) -> str:
    choice = random.choice(["slash", "dash", "epoch"])
    if choice == "slash":
        return ts.strftime("%Y/%m/%d %H:%M:%S")
    if choice == "dash":
        return ts.strftime("%d-%b-%Y %H:%M:%S")
    return str(int(ts.timestamp()))


def format_json_line(
    ts: dt.datetime, ip: str, method: str, path: str, status: int, duration_ms: int
) -> str:
    payload = {
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ip": ip,
        "method": method,
        "path": path,
        "status": status,
        "duration_ms": duration_ms,
    }
    return json.dumps(payload)


def generate_line(ts: dt.datetime) -> str:
    ip = random_ip()
    method = random.choice(METHODS)
    path = random.choice(PATHS)
    status = random.choice(STATUSES)
    duration_ms = random.randint(5, 2000)
    return format_standard_line(ts, ip, method, path, status, duration_ms)


def generate_anomaly(ts: dt.datetime) -> str:
    ip = random_ip()
    method = random.choice(METHODS)
    path = random.choice(PATHS)
    status = random.choice(STATUSES)
    duration_ms = random.randint(5, 2000)

    anomaly_type = random.choice(
        [
            "alt_timestamp",
            "duration_seconds",
            "missing_status",
            "extra_fields",
            "blank",
            "malformed",
            "json",
            "partial",
        ]
    )

    if anomaly_type == "alt_timestamp":
        ts_text = format_alt_timestamp(ts)
        return f"{ts_text} {ip} {method} {path} {status} {duration_ms}ms"
    if anomaly_type == "duration_seconds":
        return f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')} {ip} {method} {path} {status} {duration_ms / 1000:.3f}s"
    if anomaly_type == "missing_status":
        return f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')} {ip} {method} {path} - {duration_ms}ms"
    if anomaly_type == "extra_fields":
        ua = random.choice(USER_AGENTS)
        ref = random.choice(REFERRERS)
        return (
            f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')} {ip} {method} {path} {status} {duration_ms}ms "
            f'"{ua}" "{ref}"'
        )
    if anomaly_type == "blank":
        return ""
    if anomaly_type == "json":
        return format_json_line(ts, ip, method, path, status, duration_ms)
    if anomaly_type == "partial":
        return f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')} {ip} {method}"
    return "this is not a log line"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic mixed-format log file."
    )
    parser.add_argument(
        "--lines", type=int, default=1000, help="Number of lines to generate"
    )
    parser.add_argument("--output", default="sample.log", help="Output log path")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.08,
        help="Fraction of lines that are anomalies",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    start = dt.datetime(2024, 3, 15, 14, 23, 0, tzinfo=dt.timezone.utc)
    lines: List[str] = []

    for i in range(args.lines):
        ts = start + dt.timedelta(seconds=i)
        if random.random() < args.anomaly_rate:
            lines.append(generate_anomaly(ts))
        else:
            lines.append(generate_line(ts))

    with open(args.output, "w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\n")

    print(f"Wrote {len(lines)} lines to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
