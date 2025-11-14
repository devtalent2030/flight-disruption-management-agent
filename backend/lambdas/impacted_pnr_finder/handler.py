def handler(event, _context):
    """Return mock PNRs impacted by flight_id."""
    flight_id = (event or {}).get("flight_id", "AB123")
    return {
        "flight_id": flight_id,
        "pnrs": [
            {"pnr_id": "PNR-AB123-001"},
            {"pnr_id": "PNR-AB123-002"},
            {"pnr_id": "PNR-AB123-003"},
        ],
    }
