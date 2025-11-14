from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional

import boto3

# Optional: if EVENT_BUS is set, we put to EventBridge; otherwise we just return a payload
EVENT_BUS = os.getenv("EVENT_BUS", "")
_events = boto3.client("events") if EVENT_BUS else None


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Demo generator for a flight disruption input.
    Input (optional):
      {
        "flightNo": "AB123",
        "reason": "WX"  # free text
      }
    Output:
      {
        "flightNo": "...",
        "disruption": {"reason":"...","occurredAt":"<epoch>"},
        "correlationId": "SIM-..."
      }
    """
    flight_no = event.get("flightNo", "AB123")
    reason = event.get("reason", "IRREGULAR_OPS")
    payload = {
        "flightNo": flight_no,
        "disruption": {"reason": reason, "occurredAt": int(time.time())},
        "correlationId": f"SIM-{uuid.uuid4()}",
    }

    if _events:
        _events.put_events(
            Entries=[
                {
                    "Source": "fdm.simulator",
                    "DetailType": "FlightDisruption",
                    "Detail": json_dumps(payload),
                    "EventBusName": EVENT_BUS,
                }
            ]
        )

    return payload


def json_dumps(data: Dict[str, Any]) -> str:
    # Tiny local helper avoids importing json at module top if you care about cold start micro-optimizations
    import json  # noqa: WPS433

    return json.dumps(data)
