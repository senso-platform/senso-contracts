#!/usr/bin/env python3
"""Validate MQTT examples against envelope + payload schemas.

Rules mirrored from ingest (INIT-PLAN phase 6):
  * every example must satisfy mqtt/envelope.schema.json;
  * payload must satisfy payloads/<type>.schema.json;
  * semantic rule not expressible in JSON Schema: sentAt (and TELEMETRY sample ts)
    must not be more than 5 minutes in the future (ADR-0001 §6.4.4).

valid/* must pass all checks; invalid/* must fail at least one (the file name says which).
The channel↔type check needs the MQTT topic and is covered by ingest tests, not here.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatError

ROOT = Path(__file__).resolve().parent.parent
MQTT = ROOT / "mqtt"
FUTURE_TOLERANCE = timedelta(minutes=5)

PAYLOAD_BY_TYPE = {
    "TELEMETRY": "telemetry.schema.json",
    "DEVICE_DISCOVERED": "device-discovered.schema.json",
    "DEVICE_INVENTORY": "device-inventory.schema.json",
    "SECURITY_EVENT": "security-event.schema.json",
    "GATEWAY_STATUS": "gateway-status.schema.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def schema_errors(doc: dict, schema: dict) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in validator.iter_errors(doc)]


def time_window_errors(doc: dict) -> list[str]:
    limit = datetime.now(timezone.utc) + FUTURE_TOLERANCE
    errors = []
    try:
        if parse_ts(doc["sentAt"]) > limit:
            errors.append(f"sentAt {doc['sentAt']} is more than {FUTURE_TOLERANCE} in the future")
        for i, sample in enumerate(doc.get("payload", {}).get("samples", [])):
            ts = sample.get("ts")
            if ts and parse_ts(ts) > limit:
                errors.append(f"samples[{i}].ts {ts} is more than {FUTURE_TOLERANCE} in the future")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"cannot check timestamps: {exc}")
    return errors


def check(doc: dict, envelope_schema: dict) -> list[str]:
    errors = schema_errors(doc, envelope_schema)
    payload_file = PAYLOAD_BY_TYPE.get(doc.get("type"))
    if payload_file:
        errors += schema_errors(doc.get("payload", {}), load(MQTT / "payloads" / payload_file))
    elif doc.get("type") is not None:
        errors.append(f"unknown message type {doc.get('type')!r}")
    errors += time_window_errors(doc)
    return errors


def main() -> int:
    envelope_schema = load(MQTT / "envelope.schema.json")
    failures = 0

    for path in sorted((MQTT / "examples" / "valid").glob("*.json")):
        errors = check(load(path), envelope_schema)
        if errors:
            failures += 1
            print(f"FAIL valid/{path.name} unexpectedly rejected:")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"ok   valid/{path.name}")

    for path in sorted((MQTT / "examples" / "invalid").glob("*.json")):
        errors = check(load(path), envelope_schema)
        if not errors:
            failures += 1
            print(f"FAIL invalid/{path.name} was accepted but must be rejected")
        else:
            reason = errors[0]
            print(f"ok   invalid/{path.name} rejected: {reason[:140]}{'...' if len(reason) > 140 else ''}")

    print(f"\n{'VALIDATION FAILED' if failures else 'ALL EXAMPLES OK'} ({failures} problem(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
