def score_options(pnr):
    """Return ranked rebooking options (mock)."""
    return [
        {"flightNo":"AB456","origin":"YYZ","destination":"YVR","dep":"10:05","arr":"12:25","stops":0,"cabin":"Economy","arrivalDelta":45},
        {"flightNo":"AB789","origin":"YYZ","destination":"YVR","dep":"12:30","arr":"14:50","stops":1,"cabin":"Economy","arrivalDelta":180},
    ]
