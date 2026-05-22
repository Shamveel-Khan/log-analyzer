from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple

from analyze import analyze_log, parse_timestamp


def format_count_pct(count: int, total: int) -> str:
    if total <= 0:
        return f"{count} (n/a)"
    pct = (count / total) * 100.0
    return f"{count} ({pct:.1f}%)"


def summarize_status(status_counts: Dict[int, int]) -> Tuple[int, int, int]:
    total = sum(status_counts.values())
    error_count = 0
    for code, count in status_counts.items():
        if 400 <= int(code) <= 599:
            error_count += count
    return total, error_count, total - error_count


def render_human_report(stats: Dict[str, Any], top_n: int) -> str:
    lines: List[str] = []

    lines.append("Log analyzer report")
    lines.append("-")
    lines.append(
        "Totals: "
        f"lines={stats['total_lines']}, "
        f"parsed={stats['parsed_lines']}, "
        f"malformed={stats['malformed_lines']}, "
        f"blank={stats['blank_lines']}, "
        f"json={stats['json_lines']}, "
        f"filtered_by_since={stats['filtered_lines']}, "
        f"since_missing_timestamp={stats['since_missing_timestamp']}"
    )

    ts_min = stats.get("timestamp_min")
    ts_max = stats.get("timestamp_max")
    if ts_min and ts_max:
        lines.append(f"Time range: {ts_min.isoformat()} to {ts_max.isoformat()}")

    status_counts = stats["status_counts"]
    status_total, error_count, ok_count = summarize_status(status_counts)
    if status_total > 0:
        error_rate = (error_count / status_total) * 100.0
        lines.append(
            f"Status: total={status_total}, ok={ok_count}, errors={error_count} ({error_rate:.1f}%)"
        )
    else:
        lines.append("Status: no valid status codes parsed")

    if status_counts:
        lines.append("Status breakdown:")
        for code in sorted(status_counts.keys()):
            lines.append(
                f"  {code}: {format_count_pct(status_counts[code], status_total)}"
            )

    duration_count = stats["duration_count"]
    if duration_count > 0:
        avg = stats["duration_total_ms"] / duration_count
        lines.append(
            "Durations: "
            f"count={duration_count}, "
            f"avg_ms={avg:.1f}, "
            f"min_ms={stats['duration_min_ms']:.1f}, "
            f"max_ms={stats['duration_max_ms']:.1f}"
        )
    else:
        lines.append("Durations: no valid durations parsed")

    ip_counts = stats["ip_counts"]
    if ip_counts:
        lines.append(f"Top {top_n} IPs:")
        for ip, count in sorted(
            ip_counts.items(), key=lambda item: (-item[1], item[0])
        )[:top_n]:
            lines.append(f"  {ip}: {count}")
    else:
        lines.append("Top IPs: none")

    anomaly_counts = stats["anomaly_counts"]
    if anomaly_counts:
        lines.append("Anomalies:")
        for name, count in sorted(
            anomaly_counts.items(), key=lambda item: (-item[1], item[0])
        ):
            lines.append(f"  {name}: {count}")

    endpoint_summaries = stats.get("endpoint_summaries", [])
    if endpoint_summaries:
        lines.append(f"Top {top_n} endpoints by p95 (ms):")
        ranked = sorted(
            endpoint_summaries,
            key=lambda item: (
                -(item.get("p95_ms") or 0.0),
                -(item.get("avg_ms") or 0.0),
                item["endpoint"],
            ),
        )[:top_n]
        for item in ranked:
            lines.append(
                "  "
                f"{item['endpoint']}: p95={item.get('p95_ms')}, "
                f"avg={item.get('avg_ms')}, count={item.get('count')}"
            )

    return "\n".join(lines)


def build_json_report(stats: Dict[str, Any], top_n: int) -> Dict[str, Any]:
    status_counts = stats["status_counts"]
    status_total, error_count, ok_count = summarize_status(status_counts)

    ip_counts = stats["ip_counts"]
    top_ips = [
        {"ip": ip, "count": count}
        for ip, count in sorted(
            ip_counts.items(), key=lambda item: (-item[1], item[0])
        )[:top_n]
    ]

    ts_min = stats.get("timestamp_min")
    ts_max = stats.get("timestamp_max")

    time_buckets = []
    for bucket, bucket_stats in stats.get("time_buckets", {}).items():
        total = bucket_stats.get("total", 0)
        errors = bucket_stats.get("errors", 0)
        time_buckets.append(
            {
                "bucket": bucket.isoformat(),
                "total": total,
                "errors": errors,
                "error_rate": (errors / total) if total else None,
            }
        )

    endpoint_summaries = stats.get("endpoint_summaries", [])
    top_endpoints = sorted(
        endpoint_summaries,
        key=lambda item: (
            -(item.get("p95_ms") or 0.0),
            -(item.get("avg_ms") or 0.0),
            item["endpoint"],
        ),
    )[:top_n]

    return {
        "summary": {
            "total_lines": stats["total_lines"],
            "parsed_lines": stats["parsed_lines"],
            "malformed_lines": stats["malformed_lines"],
            "blank_lines": stats["blank_lines"],
            "json_lines": stats["json_lines"],
            "filtered_lines": stats["filtered_lines"],
            "since_missing_timestamp": stats["since_missing_timestamp"],
            "time_range": {
                "start": ts_min.isoformat() if ts_min else None,
                "end": ts_max.isoformat() if ts_max else None,
            },
        },
        "status": {
            "total": status_total,
            "ok": ok_count,
            "error": error_count,
            "counts": {str(k): v for k, v in sorted(status_counts.items())},
        },
        "duration": {
            "count": stats["duration_count"],
            "avg_ms": (
                (stats["duration_total_ms"] / stats["duration_count"])
                if stats["duration_count"]
                else None
            ),
            "min_ms": stats["duration_min_ms"],
            "max_ms": stats["duration_max_ms"],
            "percentiles_ms": stats.get("duration_percentiles", {}),
        },
        "top_ips": top_ips,
        "anomalies": dict(sorted(stats["anomaly_counts"].items())),
        "time_buckets": time_buckets,
        "endpoints": top_endpoints,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze mixed-format server logs.")
    parser.add_argument("path", nargs="?", help="Path to the log file")
    parser.add_argument("--input", help="Path to the log file (overrides positional)")
    parser.add_argument("--top", type=int, default=10, help="Top N IPs to show")
    parser.add_argument("--format", choices=["human", "json", "both"], default="human")
    parser.add_argument("--since", help="Ignore entries before this time")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.input or args.path
    if not path:
        print("error: input path required", file=sys.stderr)
        return 2

    since = None
    if args.since:
        since = parse_timestamp(args.since)
        if since is None:
            print("warning: could not parse --since, ignoring", file=sys.stderr)
            since = None

    try:
        stats = analyze_log(path, since=since)
    except FileNotFoundError:
        print("error: input file not found", file=sys.stderr)
        return 2

    if args.format in ("human", "both"):
        print(render_human_report(stats, args.top))

    if args.format in ("json", "both"):
        if args.format == "both":
            print("--- JSON ---")
        print(json.dumps(build_json_report(stats, args.top), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
