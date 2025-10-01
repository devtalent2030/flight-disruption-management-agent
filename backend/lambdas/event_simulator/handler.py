import json, uuid
from datetime import datetime

def handler(event, context):
    payload = {
        "event_id": str(uuid.uuid4()),
        "type": event.get("type", "DELAY"),
        "flight_no": event.get("flight_no", "FD123"),
        "dep": event.get("dep", "YYZ"),
        "arr": event.get("arr", "YVR"),
        "delay_min": event.get("delay_min", 45),
        "ts": datetime.utcnow().isoformat() + "Z"
    }
    return {"statusCode": 200, "body": json.dumps(payload)}
