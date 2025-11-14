from __future__ import annotations

from typing import Any, Dict, List


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Stub: given a disrupted flight, return one impacted PNR and passenger, plus raw options.
    Input:
      { "flightNo": "AB123", ... }
    Output (feeds OptionsScoring next):
      {
        "pnrId": "PNR123",
        "passenger": {"id":"PAX001","email":"pax@example.com"},
        "options": [
          {"flightNo":"AB456","departAt":"2025-12-12T09:10Z","arriveAt":"2025-12-12T12:30Z","price":320.0},
          {"flightNo":"AB789","departAt":"2025-12-12T10:40Z","arriveAt":"2025-12-12T13:55Z","price":295.0}
        ]
      }
    """
    _unused = event  # keep signature stable; you can look up real PNRs later

    options: List[Dict[str, Any]] = [
        {
            "flightNo": "AB456",
            "departAt": "2025-12-12T09:10Z",
            "arriveAt": "2025-12-12T12:30Z",
            "price": 320.0,
        },
        {
            "flightNo": "AB789",
            "departAt": "2025-12-12T10:40Z",
            "arriveAt": "2025-12-12T13:55Z",
            "price": 295.0,
        },
    ]

    return {
        "pnrId": "PNR123",
        "passenger": {"id": "PAX001", "email": "pax@example.com"},
        "options": options,
    }
