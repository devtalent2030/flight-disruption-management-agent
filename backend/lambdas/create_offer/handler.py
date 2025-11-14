from __future__ import annotations

import decimal
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3

from common.crypto import generate_token, now_epoch, sign_token

dynamodb = boto3.client("dynamodb")

OFFERS_TABLE = os.getenv("OFFERS_TABLE", "Offers")
EVENTS_TABLE = os.getenv("EVENTS_TABLE", "Events")
LINK_BASE_URL = os.getenv("LINK_BASE_URL", "https://example.com/offer")
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "")
OFFER_TTL_MINUTES = int(os.getenv("OFFER_TTL_MINUTES", "60"))


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conv(v: Any) -> Dict[str, Any]:
    if v is None:
        return {"NULL": True}
    if isinstance(v, bool):
        return {"BOOL": v}
    if isinstance(v, (int, float, decimal.Decimal)):
        return {"N": str(v)}
    if isinstance(v, str):
        return {"S": v}
    if isinstance(v, list):
        return {"L": [_conv(x) for x in v]}
    if isinstance(v, dict):
        return {"M": {k: _conv(x) for k, x in v.items()}}
    raise TypeError(f"Unsupported type: {type(v)}")


def _to_ddb(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _conv(v) for k, v in item.items()}


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    # Validate input
    pnr_id = event.get("pnrId")
    passenger = event.get("passenger") or {}
    options: List[Dict[str, Any]] = event.get("scoredOptions") or []

    if not pnr_id or not passenger.get("id"):
        raise ValueError("pnrId and passenger.id are required")

    has_options = len(options) > 0

    offer_id = "OFR-" + str(uuid.uuid4())
    token = generate_token(16)
    exp_epoch = now_epoch() + OFFER_TTL_MINUTES * 60
    signature = sign_token(token, offer_id, exp_epoch, TOKEN_SECRET)

    link = (
        f"{LINK_BASE_URL}"
        f"?offerId={offer_id}&token={token}&sig={signature}&exp={exp_epoch}"
    )

    record = {
        "offerId": offer_id,
        "pnrId": pnr_id,
        "passengerId": passenger["id"],
        "options": options,
        "selectedIndex": None,
        "status": "NO_OPTIONS" if not has_options else "PENDING",
        "expiresAt": exp_epoch,  # DynamoDB TTL
        "token": token,
        "signature": signature,
        "createdAt": _iso_now(),
    }

    # Persist Offer (idempotent on offerId)
    dynamodb.put_item(
        TableName=OFFERS_TABLE,
        Item=_to_ddb(record),
        ConditionExpression="attribute_not_exists(offerId)",
    )

    # Audit event
    ev = {
        "eventId": "EVT-" + str(uuid.uuid4()),
        "type": "OFFER_CREATED",
        "entityId": offer_id,
        "payload": {
            "pnrId": pnr_id,
            "passengerId": passenger["id"],
            "hasOptions": has_options,
        },
        "createdAt": _iso_now(),
    }
    dynamodb.put_item(TableName=EVENTS_TABLE, Item=_to_ddb(ev))

    return {
        "offerId": offer_id,
        "pnrId": pnr_id,
        "passenger": passenger,
        "link": link,
        "status": record["status"],
        "hasOptions": has_options,
    }
