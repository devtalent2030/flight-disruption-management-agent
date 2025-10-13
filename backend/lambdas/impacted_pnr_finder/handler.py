import json
def handler(event, context):
    """Return mock PNRs impacted by flight_id."""
    flight_id = event["detail"]["flight_id"] if "detail" in event else event.get("flight_id","AB123")
    impacted = [{"pnr_id":"PNR001","passenger_id":"P001","flight_id":flight_id}]
    return {"impacted": impacted}
