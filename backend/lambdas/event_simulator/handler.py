# backend/lambdas/event_simulator/handler.py
from __future__ import annotations

import os
import time
import uuid
from decimal import Decimal
from typing import Any, Dict

import boto3

REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ca-central-1"

# Optional: if you later want to write audit rows, wire this table/IAM in SAM.
EVENTS_TABLE = os.getenv("EVENTS_TABLE", "Events")
ddb = boto3.resource("dynamodb", region_name=REGION)
events_table = ddb.Table(EVENTS_TABLE)


def _now_epoch() -> int:
    return int(time.time())


def _now_iso() -> str:
    # Keep timezone-aware ISO8601.
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _json_default(o: Any) -> Any:
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    raise TypeError(f"Not JSON serializable: {type(o)}")


def json_dumps(data: Dict[str, Any]) -> str:
    # Local import to minimize cold-start surface.
    import json  # noqa: PLC0415

    return json.dumps(data, default=_json_default)


def _make_demo_payload() -> Dict[str, Any]:
    """
    Create a simple demo input for the CreateOffer Lambda / offer flow.
    """
    # Six passengers seeded on AB123 in your seeder; pick one for the demo.
    pax_email = os.getenv("DEMO_EMAIL", "pax@example.com")
    return {
        "pnrId": "PNR123",
        "passenger": {"id": "PAX001", "email": pax_email},
        "scoredOptions": [
            {
                "flightNo": "AB456",
                "departAt": "2025-12-12T09:10Z",
                "arriveAt": "2025-12-12T12:30Z",
                "price": 320.0,
                "score": 0.92,
            },
            {
                "flightNo": "AB789",
                "departAt": "2025-12-12T10:40Z",
                "arriveAt": "2025-12-12T13:55Z",
                "price": 295.0,
                "score": 0.88,
            },
        ],
        "generatedAt": _now_iso(),
    }


def _maybe_write_event(kind: str, payload: Dict[str, Any]) -> None:
    """
    Optional: write a simulator event row if EVENTS_TABLE/IAM are present.
    Fail silently if access is not allowed (keeps this Lambda purely optional).
    """
    try:
        events_table.put_item(
            Item={
                "eventId": f"SIM-{uuid.uuid4()}",
                "type": kind,
                "entityId": payload.get("pnrId", "N/A"),
                "payload": payload,
                "createdAt": _now_iso(),
            }
        )
    except Exception:
        # No IAM / table? Ignore; this is a simulator.
        pass


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # noqa: ARG001
    """
    If input already looks like a CreateOffer request, echo it.
    Otherwise, fabricate a well-formed demo payload.
    """
    if isinstance(event, dict) and "pnrId" in event and "passenger" in event:
        out = dict(event)
        out.setdefault("generatedAt", _now_iso())
        _maybe_write_event("SIM_INPUT_ECHOED", out)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
            "body": json_dumps(out),
        }

    demo = _make_demo_payload()
    _maybe_write_event("SIM_INPUT_CREATED", demo)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
        "body": json_dumps(demo),
    }
