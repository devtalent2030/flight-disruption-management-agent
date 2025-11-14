# backend/lambdas/decision_api/handler.py
from __future__ import annotations

import os
import time
import json
from typing import Any, Dict, Optional
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key  # noqa: F401

from common.crypto import sign_token

ddb = boto3.resource("dynamodb")
OFFERS_TABLE = os.getenv("OFFERS_TABLE", "Offers")
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "")
table = ddb.Table(OFFERS_TABLE)


def _now_epoch() -> int:
    return int(time.time())


def _json_default(o: Any):
    # Convert DynamoDB Decimals to JSON-friendly numbers
    if isinstance(o, Decimal):
        # keep integers as int, others as float
        return int(o) if o == o.to_integral_value() else float(o)
    # (extend here if you add more non-JSON types later)
    raise TypeError(f"Not JSON serializable: {type(o)}")


def _json(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            # CORS (optional—handy if your front-end hits this directly)
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body, default=_json_default),
    }


def _get_event_method(event: Dict[str, Any]) -> str:
    return event.get("httpMethod", "GET").upper()


def _get_route(event: Dict[str, Any]) -> str:
    # e.g. /offer/{token}, /offer/{token}/accept
    return event.get("path", "") or ""


def _qs(event: Dict[str, Any]) -> Dict[str, str]:
    return event.get("queryStringParameters") or {}


def _path_token(event: Dict[str, Any]) -> Optional[str]:
    pp = event.get("pathParameters") or {}
    token = pp.get("token")
    if token:
        return token
    # Fallback: try to slice from path
    path = event.get("path", "") or ""
    parts = [p for p in path.split("/") if p]
    if "offer" in parts:
        idx = parts.index("offer")
        if len(parts) > idx + 1:
            return parts[idx + 1]
    return None


def _validate_link(qs: Dict[str, str]) -> Dict[str, str]:
    offer_id = qs.get("offerId")
    sig = qs.get("sig")
    exp = qs.get("exp")
    if not (offer_id and sig and exp):
        raise ValueError("Missing offerId/sig/exp query parameters")
    return {"offerId": offer_id, "sig": sig, "exp": exp}


def _load_offer(offer_id: str) -> Dict[str, Any]:
    resp = table.get_item(Key={"offerId": offer_id})
    item = resp.get("Item")
    if not item:
        raise LookupError("Offer not found")
    return item


def _verify_signature(token: str, offer_id: str, exp_str: str, sig: str, item: Dict[str, Any]) -> None:
    try:
        exp = int(exp_str)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid exp") from exc
    if _now_epoch() > exp:
        raise PermissionError("Link expired")

    if token != item.get("token"):
        raise PermissionError("Token mismatch")

    expect = sign_token(token, offer_id, exp, TOKEN_SECRET)
    if sig != expect:
        raise PermissionError("Bad signature")


def _get_handler(offer: Dict[str, Any]) -> Dict[str, Any]:
    # Trim to public payload; leave numbers as Decimal—_json() will serialize them safely
    return {
        "offerId": offer["offerId"],
        "status": offer.get("status", "PENDING"),
        "selectedIndex": offer.get("selectedIndex"),
        "options": offer.get("options", []),
        "expiresAt": offer.get("expiresAt"),
        "pnrId": offer.get("pnrId"),
        "passengerId": offer.get("passengerId"),
    }


def _post_next(offer_id: str, offer: Dict[str, Any]) -> Dict[str, Any]:
    options = offer.get("options", [])
    if not options:
        return {"offerId": offer_id, "message": "no options"}

    current = offer.get("selectedIndex")
    next_idx = 0 if current is None else int(current) + 1
    if next_idx >= len(options):
        return {"offerId": offer_id, "message": "no more options"}

    table.update_item(
        Key={"offerId": offer_id},
        UpdateExpression="SET selectedIndex = :i",
        ExpressionAttributeValues={":i": next_idx},
    )
    return {"offerId": offer_id, "selectedIndex": next_idx}


def _post_accept(offer_id: str) -> Dict[str, Any]:
    table.update_item(
        Key={"offerId": offer_id},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "ACCEPTED"},
    )
    return {"offerId": offer_id, "status": "ACCEPTED"}


def _post_decline(offer_id: str) -> Dict[str, Any]:
    table.update_item(
        Key={"offerId": offer_id},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "DECLINED"},
    )
    return {"offerId": offer_id, "status": "DECLINED"}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # noqa: ARG001
    try:
        method = _get_event_method(event)
        route = _get_route(event)
        token = _path_token(event)
        if not token:
            return _json(400, {"message": "missing token in path"})

        qs = _qs(event)
        parsed = _validate_link(qs)
        offer_id, sig, exp = parsed["offerId"], parsed["sig"], parsed["exp"]

        item = _load_offer(offer_id)
        _verify_signature(token, offer_id, exp, sig, item)

        if method == "GET":
            return _json(200, _get_handler(item))

        if method == "POST":
            if route.endswith("/next"):
                return _json(200, _post_next(offer_id, item))
            if route.endswith("/accept"):
                return _json(200, _post_accept(offer_id))
            if route.endswith("/decline"):
                return _json(200, _post_decline(offer_id))
            return _json(404, {"message": "unknown POST route"})

        return _json(405, {"message": "method not allowed"})

    except PermissionError as e:  # expired / bad token / bad sig
        return _json(403, {"message": str(e)})
    except LookupError as e:
        return _json(404, {"message": str(e)})
    except ValueError as e:
        return _json(400, {"message": str(e)})
    except Exception:
        # last-resort catcher to avoid 502s
        return _json(500, {"message": "Internal server error"})
