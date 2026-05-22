from __future__ import annotations

import datetime as dt
import json
import re
import shlex
from typing import Any, Dict, List, Optional, Tuple

IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$|^[0-9a-fA-F:]+$")


TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%d-%b-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M",
]


def parse_timestamp(value: str) -> Optional[dt.datetime]:
    v = value.strip()
    if not v:
        return None

    if re.fullmatch(r"\d{10,13}", v):
        ts = int(v)
        if len(v) == 13:
            ts = ts / 1000.0
        return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)

    try:
        iso = v.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(iso)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except ValueError:
        pass

    for fmt in TIMESTAMP_FORMATS:
        try:
            parsed = dt.datetime.strptime(v, fmt)
            return parsed.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue

    return None


def parse_duration_token(token: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    if token is None:
        return None, "missing_duration"
    t = token.strip()
    if not t or t == "-":
        return None, "missing_duration"

    try:
        if t.endswith("ms"):
            return float(t[:-2]), None
        if t.endswith("s"):
            return float(t[:-1]) * 1000.0, None
        return float(t), None
    except ValueError:
        return None, "invalid_duration"


def parse_duration_value(
    value: Any, key_hint: str = ""
) -> Tuple[Optional[float], Optional[str]]:
    if value is None:
        return None, "missing_duration"
    if isinstance(value, (int, float)):
        return float(value), None
    return parse_duration_token(str(value))


def parse_status_token(token: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    if token is None:
        return None, "missing_status"
    t = token.strip()
    if not t or t == "-":
        return None, "missing_status"
    if t.isdigit():
        return int(t), None
    return None, "invalid_status"


def first_value(data: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def parse_json_line(data: Dict[str, Any]) -> Dict[str, Any]:
    anomalies: List[str] = []

    ts_value = first_value(data, ["timestamp", "time", "ts", "date"])
    timestamp = parse_timestamp(str(ts_value)) if ts_value is not None else None
    if timestamp is None:
        anomalies.append("missing_timestamp")

    ip_value = first_value(data, ["ip", "ip_address", "client_ip", "remote_addr"])
    ip = str(ip_value) if ip_value is not None else None
    if ip and not IP_RE.match(ip):
        anomalies.append("bad_ip")

    method_value = first_value(data, ["method", "http_method", "verb"])
    method = str(method_value).upper() if method_value is not None else None
    if method is None:
        anomalies.append("missing_method")

    path_value = first_value(data, ["path", "uri", "url", "endpoint"])
    path = str(path_value) if path_value is not None else None
    if path is None:
        anomalies.append("missing_path")

    status_value = first_value(data, ["status", "status_code", "code", "http_status"])
    status, status_issue = (
        parse_status_token(str(status_value))
        if status_value is not None
        else (None, "missing_status")
    )
    if status_issue:
        anomalies.append(status_issue)

    duration_key = None
    for key in [
        "duration_ms",
        "response_time_ms",
        "latency_ms",
        "duration",
        "response_time",
        "latency",
        "rt",
    ]:
        if key in data:
            duration_key = key
            break
    duration_value = data.get(duration_key) if duration_key else None
    duration_ms, duration_issue = parse_duration_value(
        duration_value, duration_key or ""
    )
    if duration_issue:
        anomalies.append(duration_issue)

    recognized = any([timestamp, ip, method, path, status, duration_ms is not None])
    if not recognized:
        return {
            "kind": "malformed",
            "parsed": False,
            "anomalies": anomalies + ["json_unrecognized_fields"],
            "data": {},
        }

    return {
        "kind": "json",
        "parsed": True,
        "anomalies": anomalies,
        "data": {
            "timestamp": timestamp,
            "ip": ip,
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": duration_ms,
        },
    }


def parse_standard_line(raw: str) -> Dict[str, Any]:
    anomalies: List[str] = []

    try:
        tokens = shlex.split(raw, posix=True)
    except ValueError:
        tokens = raw.split()
        anomalies.append("tokenize_error")

    if not tokens:
        return {
            "kind": "malformed",
            "parsed": False,
            "anomalies": anomalies + ["empty_tokens"],
            "data": {},
        }

    timestamp = parse_timestamp(tokens[0])
    idx = 1
    if timestamp is None and len(tokens) >= 2:
        timestamp = parse_timestamp(f"{tokens[0]} {tokens[1]}")
        if timestamp is not None:
            idx = 2

    if timestamp is None:
        return {
            "kind": "malformed",
            "parsed": False,
            "anomalies": anomalies + ["missing_timestamp"],
            "data": {},
        }

    if len(tokens) < idx + 3:
        return {
            "kind": "malformed",
            "parsed": False,
            "anomalies": anomalies + ["too_few_fields"],
            "data": {},
        }

    ip = tokens[idx]
    method = tokens[idx + 1] if len(tokens) > idx + 1 else None
    path = tokens[idx + 2] if len(tokens) > idx + 2 else None
    status_token = tokens[idx + 3] if len(tokens) > idx + 3 else None
    duration_token = tokens[idx + 4] if len(tokens) > idx + 4 else None

    if ip and not IP_RE.match(ip):
        anomalies.append("bad_ip")

    status, status_issue = parse_status_token(status_token)
    if status_issue:
        anomalies.append(status_issue)

    duration_ms, duration_issue = parse_duration_token(duration_token)
    if duration_issue:
        anomalies.append(duration_issue)

    if method is None:
        anomalies.append("missing_method")
    if path is None:
        anomalies.append("missing_path")

    return {
        "kind": "parsed",
        "parsed": True,
        "anomalies": anomalies,
        "data": {
            "timestamp": timestamp,
            "ip": ip,
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": duration_ms,
        },
    }


def parse_line(line: str) -> Dict[str, Any]:
    raw = line.rstrip("\n")
    if not raw.strip():
        return {
            "kind": "blank",
            "parsed": False,
            "anomalies": ["blank_line"],
            "data": {},
        }

    if raw.lstrip().startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "kind": "malformed",
                "parsed": False,
                "anomalies": ["json_decode_error"],
                "data": {},
            }
        if isinstance(data, dict):
            return parse_json_line(data)
        return {
            "kind": "malformed",
            "parsed": False,
            "anomalies": ["json_not_object"],
            "data": {},
        }

    return parse_standard_line(raw)


def is_error_status(status: Optional[int]) -> bool:
    return status is not None and 400 <= int(status) <= 599


def bucket_timestamp(timestamp: dt.datetime, bucket_seconds: int) -> dt.datetime:
    if bucket_seconds <= 0:
        bucket_seconds = 60
    epoch = int(timestamp.timestamp())
    bucket_start = epoch - (epoch % bucket_seconds)
    return dt.datetime.fromtimestamp(bucket_start, tz=dt.timezone.utc)


def compute_percentiles(
    values: List[float], percentiles: List[float]
) -> Dict[str, Optional[float]]:
    if not values:
        return {f"p{int(p)}": None for p in percentiles}
    sorted_vals = sorted(values)
    last = len(sorted_vals) - 1
    results: Dict[str, Optional[float]] = {}
    for p in percentiles:
        if last <= 0:
            results[f"p{int(p)}"] = sorted_vals[0]
            continue
        rank = p / 100.0 * last
        low = int(rank)
        high = min(low + 1, last)
        frac = rank - low
        results[f"p{int(p)}"] = (
            sorted_vals[low] + (sorted_vals[high] - sorted_vals[low]) * frac
        )
    return results


def summarize_status(status_counts: Dict[int, int]) -> Tuple[int, int, int]:
    total = sum(status_counts.values())
    error_count = 0
    for code, count in status_counts.items():
        if 400 <= int(code) <= 599:
            error_count += count
    return total, error_count, total - error_count


def analyze_log(
    path: str,
    since: Optional[dt.datetime] = None,
    bucket_seconds: int = 60,
) -> Dict[str, Any]:
    stats: Dict[str, Any] = {
        "total_lines": 0,
        "parsed_lines": 0,
        "blank_lines": 0,
        "malformed_lines": 0,
        "json_lines": 0,
        "filtered_lines": 0,
        "since_missing_timestamp": 0,
        "status_counts": {},
        "ip_counts": {},
        "anomaly_counts": {},
        "duration_count": 0,
        "duration_total_ms": 0.0,
        "duration_min_ms": None,
        "duration_max_ms": None,
        "timestamp_min": None,
        "timestamp_max": None,
        "time_buckets": {},
        "endpoint_stats": {},
        "duration_values": [],
        "duration_percentiles": {},
        "endpoint_summaries": [],
    }

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stats["total_lines"] += 1
            result = parse_line(line)

            for anomaly in result["anomalies"]:
                stats["anomaly_counts"][anomaly] = (
                    stats["anomaly_counts"].get(anomaly, 0) + 1
                )

            if result["kind"] == "blank":
                stats["blank_lines"] += 1
                continue
            if result["kind"] == "malformed":
                stats["malformed_lines"] += 1
                continue
            if result["kind"] == "json":
                stats["json_lines"] += 1

            if result.get("parsed"):
                stats["parsed_lines"] += 1

            data = result.get("data", {})
            timestamp = data.get("timestamp")
            if timestamp is not None:
                if stats["timestamp_min"] is None or timestamp < stats["timestamp_min"]:
                    stats["timestamp_min"] = timestamp
                if stats["timestamp_max"] is None or timestamp > stats["timestamp_max"]:
                    stats["timestamp_max"] = timestamp

            if since is not None:
                if timestamp is None:
                    stats["since_missing_timestamp"] += 1
                    continue
                if timestamp < since:
                    stats["filtered_lines"] += 1
                    continue

            status = data.get("status")
            if status is not None:
                status_counts = stats["status_counts"]
                status_counts[status] = status_counts.get(status, 0) + 1

            ip = data.get("ip")
            if ip:
                ip_counts = stats["ip_counts"]
                ip_counts[ip] = ip_counts.get(ip, 0) + 1

            duration_ms = data.get("duration_ms")
            if duration_ms is not None:
                stats["duration_count"] += 1
                stats["duration_total_ms"] += duration_ms
                stats["duration_values"].append(duration_ms)
                if (
                    stats["duration_min_ms"] is None
                    or duration_ms < stats["duration_min_ms"]
                ):
                    stats["duration_min_ms"] = duration_ms
                if (
                    stats["duration_max_ms"] is None
                    or duration_ms > stats["duration_max_ms"]
                ):
                    stats["duration_max_ms"] = duration_ms

            if timestamp is not None:
                bucket = bucket_timestamp(timestamp, bucket_seconds)
                bucket_stats = stats["time_buckets"].setdefault(
                    bucket, {"total": 0, "errors": 0}
                )
                bucket_stats["total"] += 1
                if is_error_status(status):
                    bucket_stats["errors"] += 1

            method = data.get("method")
            path = data.get("path")
            if method and path:
                endpoint_key = f"{method} {path}"
                endpoint_stats = stats["endpoint_stats"].setdefault(
                    endpoint_key,
                    {
                        "count": 0,
                        "error_count": 0,
                        "duration_count": 0,
                        "duration_sum": 0.0,
                        "duration_min": None,
                        "duration_max": None,
                        "durations": [],
                    },
                )
                endpoint_stats["count"] += 1
                if is_error_status(status):
                    endpoint_stats["error_count"] += 1
                if duration_ms is not None:
                    endpoint_stats["duration_count"] += 1
                    endpoint_stats["duration_sum"] += duration_ms
                    endpoint_stats["durations"].append(duration_ms)
                    if (
                        endpoint_stats["duration_min"] is None
                        or duration_ms < endpoint_stats["duration_min"]
                    ):
                        endpoint_stats["duration_min"] = duration_ms
                    if (
                        endpoint_stats["duration_max"] is None
                        or duration_ms > endpoint_stats["duration_max"]
                    ):
                        endpoint_stats["duration_max"] = duration_ms

    stats["duration_percentiles"] = compute_percentiles(
        stats["duration_values"], [50, 95, 99]
    )
    endpoint_summaries: List[Dict[str, Any]] = []
    for endpoint, endpoint_stats in stats["endpoint_stats"].items():
        durations = endpoint_stats["durations"]
        percentiles = compute_percentiles(durations, [50, 95, 99])
        duration_avg = (
            endpoint_stats["duration_sum"] / endpoint_stats["duration_count"]
            if endpoint_stats["duration_count"]
            else None
        )
        error_rate = (
            endpoint_stats["error_count"] / endpoint_stats["count"]
            if endpoint_stats["count"]
            else None
        )
        endpoint_summaries.append(
            {
                "endpoint": endpoint,
                "count": endpoint_stats["count"],
                "error_count": endpoint_stats["error_count"],
                "error_rate": error_rate,
                "duration_count": endpoint_stats["duration_count"],
                "avg_ms": duration_avg,
                "min_ms": endpoint_stats["duration_min"],
                "max_ms": endpoint_stats["duration_max"],
                "p50_ms": percentiles.get("p50"),
                "p95_ms": percentiles.get("p95"),
                "p99_ms": percentiles.get("p99"),
            }
        )
    stats["endpoint_summaries"] = endpoint_summaries

    stats["time_buckets"] = dict(
        sorted(stats["time_buckets"].items(), key=lambda x: x[0])
    )

    return stats


def build_json_report(stats: Dict[str, Any], top_n: int = 10) -> Dict[str, Any]:
    status_counts = stats.get("status_counts", {})
    status_total, error_count, ok_count = summarize_status(status_counts)

    ip_counts = stats.get("ip_counts", {})
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
            "total_lines": stats.get("total_lines", 0),
            "parsed_lines": stats.get("parsed_lines", 0),
            "malformed_lines": stats.get("malformed_lines", 0),
            "blank_lines": stats.get("blank_lines", 0),
            "json_lines": stats.get("json_lines", 0),
            "filtered_lines": stats.get("filtered_lines", 0),
            "since_missing_timestamp": stats.get("since_missing_timestamp", 0),
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
            "count": stats.get("duration_count", 0),
            "avg_ms": (
                (stats.get("duration_total_ms", 0.0) / stats.get("duration_count", 0))
                if stats.get("duration_count")
                else None
            ),
            "min_ms": stats.get("duration_min_ms"),
            "max_ms": stats.get("duration_max_ms"),
            "percentiles_ms": stats.get("duration_percentiles", {}),
        },
        "top_ips": top_ips,
        "anomalies": dict(sorted(stats.get("anomaly_counts", {}).items())),
        "time_buckets": time_buckets,
        "endpoints": top_endpoints,
    }
