import os, json, boto3, time, uuid
bus = os.getenv("EVENT_BUS", "default")
evb = boto3.client("events")

def handler(event, context):
    """Simulate a disruption event."""
    detail = {
        "event_id": str(uuid.uuid4()),
        "flight_id": event.get("flight_id","AB123"),
        "status": event.get("status","CANCELLED"),
        "timestamp": int(time.time()*1000),
    }
    evb.put_events(Entries=[{
        "Source":"fdma.simulator",
        "DetailType":"flight.status_changed",
        "Detail": json.dumps(detail),
        "EventBusName": bus
    }])
    return {"ok": True, "detail": detail}
