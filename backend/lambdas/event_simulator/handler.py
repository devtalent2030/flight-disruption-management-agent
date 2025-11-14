import os
import time
import uuid

import boto3

_EVENT_BUS = os.getenv("EVENT_BUS", "default")
_evb = boto3.client("events")


def handler(event, _context):
    # Minimal synthetic “disruption” event
    entry = {
        "Source": "fdma.simulator",
        "DetailType": "FlightDisruption",
        "Detail": __import__("json").dumps(
            {
                "id": f"SIM-{uuid.uuid4().hex[:12]}",
                "flightId": event.get("flightId", "AB123"),
                "disruptedAt": int(time.time()),
            }
        ),
        "EventBusName": _EVENT_BUS,
    }
    resp = _evb.put_events(Entries=[entry])
    return {"put": resp.get("Entries", []), "failed": resp.get("FailedEntryCount", 0)}
