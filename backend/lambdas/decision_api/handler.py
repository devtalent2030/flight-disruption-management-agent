import hashlib
import os
import time
from typing import Dict, Any

import boto3

_ddb = boto3.resource("dynamodb")
_table = _ddb.Table(os.getenv("OFFERS_TABLE", "Offers"))

_SIG_SECRET = os.getenv("LINK_SIG_SECRET", "dev-secret")


def _res(code: int, body: Dict[str, Any]):
    return {
        "statusCode": code,
        "headers": {"content-type": "application/json"},
        "body": __import__("json").dumps(body),
    }


def _verify(sig: str, offer_id: str, exp: int) -> bool:
    payload = f"{offer_id}:{exp}:{_SIG_SECRET}".encode("utf-8")
    expected = hashlib.sha256(payload).hexdigest()
    if not __eq_const(sig, expected):
        return False
    if int(time.time()) > int(exp):
        return False
    return True


def __eq_const(a: str, b: str) -> bool:
    # constant-time-ish comparison
    if len(a) != len(b):
        return False
    out = 0
    for x, y in zip(a.encode(), b.encode()):
        out |= x ^ y
    return out == 0


def _get_path(event) -> str:
    # HTTP API v2 puts it here; fallbacks for local testing
    ctx = event.get("requestContext", {})
    http = ctx.get("http", {})
    return http.get("path") or event.get("path", "/")


def _get_query(event) -> Dict[str, str]:
    return event.get("queryStringParameters") or {}


def _load_offer(offer_id: str) -> Dict[str, Any]:
    res = _table.get_item(Key={"offer_id": offer_id})
    return res.get("Item")


def handler(event, _context):
    """
    Routes:
      GET  /offer/{token}?offerId=&sig=&exp=
      POST /offer/{token}/accept
      POST /offer/{token}/next
      POST /offer/{token}/decline
    (token is not used server-side; it’s included in the URL for demo UX)
    """
    path = _get_path(event)
    query = _get_query(event)  # expects offerId, sig, exp
    offer_id = (query.get("offerId") or "").strip()
    sig = (query.get("sig") or "").strip()
    exp = int(query.get("exp") or "0")

    if not offer_id or not sig or not exp:
        return _res(400, {"message": "offerId/sig/exp required"})

    if not _verify(sig, offer_id, exp):
        return _res(403, {"message": "link invalid or expired"})

    offer = _load_offer(offer_id)
    if not offer:
        return _res(404, {"message": "offer not found"})

    # GET = read
    if event.get("requestContext", {}).get("http", {}).get("method", "GET") == "GET":
        idx = offer.get("current_index", 0)
        options = offer.get("options", [])
        current = options[idx] if 0 <= idx < len(options) else None
        return _res(
            200,
            {
                "offerId": offer_id,
                "status": offer.get("status"),
                "currentIndex": idx,
                "optionsCount": len(options),
                "currentOption": current,
            },
        )

    # POST actions
    route = path  # already includes /offer/... suffixes

    if route.endswith("/accept"):
        _table.update_item(
            Key={"offer_id": offer_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "ACCEPTED"},
        )
        return _res(200, {"message": "accepted", "offerId": offer_id})

    if route.endswith("/decline"):
        _table.update_item(
            Key={"offer_id": offer_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "DECLINED"},
        )
        return _res(200, {"message": "declined", "offerId": offer_id})

    if route.endswith("/next"):
        next_idx = offer.get("current_index", 0) + 1
        options_len = len(offer.get("options", []))
        if next_idx >= options_len:
            return _res(410, {"message": "no more options"})
        _table.update_item(
            Key={"offer_id": offer_id},
            UpdateExpression="SET current_index = :i",
            ExpressionAttributeValues={":i": next_idx},
        )
        return _res(200, {"message": "advanced", "currentIndex": next_idx})

    return _res(404, {"message": "unknown route"})
