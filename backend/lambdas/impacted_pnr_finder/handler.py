import json

def handler(event, context):
    body = event.get("body") if isinstance(event, dict) else {}
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            body = {}
    flight = body.get("flight_no", "FD123")
    impacted = [{"pnr": "ABC123", "passenger": "Jane Doe"}, {"pnr": "XYZ789", "passenger": "John Lee"}]
    return {"statusCode": 200, "body": json.dumps({"flight_no": flight, "impacted": impacted})}
