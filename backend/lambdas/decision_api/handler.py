from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple

import boto3

from common.crypto import sign_token

ddb = boto3.resource("dynamodb")
offers = ddb.Table(os.getenv("OFFERS_TABLE", "Offers"))
events = ddb.Table(os.getenv("EVENTS_TABLE", "Events"))

TOKEN_SECRET = os.getenv("TOKEN_SECRET", "")


def _res(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _verify_params(event: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
    """Extract and basic-verify offerId, token, exp, sig."""
    params = event.get("queryStringParameters") or {}
    offer_id = params.get("offerId")
    sig = params.get("sig")
    exp_str = params.get("exp")
    token = None
    path_params = event.get("pathParameters") or {}
    if "token" in path_params:
        token = path_params["token"]
    elif params.get("token"):
        token = params["token"]

    exp_int = None
    if exp_str and exp_str.isdigit():
        exp_int = int(exp_str)

    return offer_id, token, exp_int, sig


def _verify_signature(offer_id: str, token: str, exp: int, sig: str) -> Optional[str]:
    if not TOKEN_SECRET:
        return "server TOKEN_SECRET not configured"
    if int(time.time()) > exp:
        return "link expired"
    expected = sign_token(token, offer_id, exp, TOKEN_SECRET)
    if sig != expected:
        return "invalid signature"
    return None


def _emit_event(evt_type: str, entity_id: str, payload: Dict[str, Any]) -> None:
    events.put_item(
        Item={
            "eventId": f"EVT-{int(time.time()*1000)}-{evt_type}",
            "type": evt_type,
            "entityId": entity_id,
            "payload": payload,
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    method = event.get("httpMethod", "GET")
    path = event.get("path", "")

    offer_id, token, exp, sig = _verify_params(event)
    if not offer_id or not token or exp is None or not sig:
        return _res(400, {"message": "missing offerId/token/exp/sig"})

    err = _verify_signature(offer_id, token, exp, sig)
    if err:
        return _res(403, {"message": err})

    # Load offer
    got = offers.get_item(Key={"offerId": offer_id}).get("Item")
    if not got:
        return _res(404, {"message": "offer not found"})

    # Normalize selectedIndex & options
    options = got.get("options") or []
    sel = got.get("selectedIndex", None)

    # Route handling
    if method == "GET" and path.endswith(f"/offer/{token}"):
        return _res(
            200,
            {
                "offerId": offer_id,
                "status": got.get("status", "PENDING"),
                "selectedIndex": sel,
                "optionsCount": len(options),
                "expiresAt": got.get("expiresAt"),
            },
        )

    if method == "POST" and path.endswith(f"/offer/{token}/next"):
        next_idx = 0 if sel is None else sel + 1
        if next_idx >= len(options):
            return _res(410, {"message": "no more options"})
        offers.update_item(
            Key={"offerId": offer_id},
            UpdateExpression="SET selectedIndex = :i",
            ExpressionAttributeValues={":i": next_idx},
        )
        _emit_event("OFFER_NEXT", offer_id, {"index": next_idx})
        return _res(200, {"offerId": offer_id, "selectedIndex": next_idx})

    if method == "POST" and path.endswith(f"/offer/{token}/accept"):
        offers.update_item(
            Key={"offerId": offer_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "ACCEPTED"},
        )
        _emit_event("OFFER_ACCEPTED", offer_id, {"selectedIndex": sel})
        return _res(200, {"offerId": offer_id, "status": "ACCEPTED"})

    if method == "POST" and path.endswith(f"/offer/{token}/decline"):
        offers.update_item(
            Key={"offerId": offer_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "DECLINED"},
        )
        _emit_event("OFFER_DECLINED", offer_id, {})
        return _res(200, {"offerId": offer_id, "status": "DECLINED"})

    return _res(404, {"message": "route not found"})
