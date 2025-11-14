from __future__ import annotations

from typing import Any, Dict, List


def _score_option(opt: Dict[str, Any]) -> float:
    """
    Toy scoring:
      - Lower price is better
      - Earlier departAt slightly preferred (lexicographic ISO sort as proxy)
    Produces a 0..1 score.
    """
    price = float(opt.get("price", 9999.0))
    # Normalize price to a 0..1 penalty (≤300 = best, ≥500 = worst)
    if price <= 300:
        price_penalty = 0.0
    elif price >= 500:
        price_penalty = 1.0
    else:
        price_penalty = (price - 300.0) / 200.0

    # Simple depart preference: earlier => tiny boost
    depart = str(opt.get("departAt", "9999-12-31T23:59Z"))
    depart_boost = 0.1 if depart <= "2025-12-12T10:00Z" else 0.0

    raw = 1.0 - price_penalty + depart_boost
    # clamp 0..1
    return max(0.0, min(1.0, raw))


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Input:
      { "options": [ ... ], ... }  # passes through other fields
    Output:
      { "scoredOptions": [ ... ], ... }  # preserves original fields
    """
    options: List[Dict[str, Any]] = event.get("options") or []
    scored: List[Dict[str, Any]] = []
    for o in options:
        s = dict(o)
        s["score"] = round(_score_option(o), 4)
        scored.append(s)

    # Highest score first
    scored.sort(key=lambda x: x.get("score", 0.0), reverse=True)

    out = dict(event)
    out["scoredOptions"] = scored
    return out
