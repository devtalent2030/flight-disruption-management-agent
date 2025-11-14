import hashlib
import os
import time
import uuid

import boto3

_ddb = boto3.resource("dynamodb")
_table = _ddb.Table(os.getenv("OFFERS_TABLE", "Offers"))

_LINK_BASE = os.getenv("LinkBaseUrl", "https://example.com/offer")
_TTL_MIN = int(os.getenv("OfferTtlMinutes", "60"))
_SIG_SECRET = os.getenv("LINK_SIG_SECRET", "dev-secret")


def _sign(offer_id: str, exp: int) -> str:
    payload = f"{offer_id}:{exp}:{_SIG_SECRET}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def handler(event, _context):
    """
    Expects:
    {
      "pnrId": "PNR-AB123-001",
      "passenger": {"id":"pax001","email":"...","name":"..."},
      "scoredOptions": [...]
    }
    """
    pnr_id = event.get("pnrId")
    passenger = event.get("passenger", {})
    options = event.get("scoredOptions", [])

    offer_id = f"OFR-{uuid.uuid4()}"
    now_s = int(time.time())
    exp_s = now_s + (_TTL_MIN * 60)
    sig = _sign(offer_id, exp_s)

    link = (
        f"{_LINK_BASE}"
        f"?offerId={offer_id}"
        f"&token={uuid.uuid4().hex[:24]}"
        f"&sig={sig}"
        f"&exp={exp_s}"
    )

    item = {
        "offer_id": offer_id,
        "pnr_id": pnr_id,
        "passenger": passenger,
        "options": options,
        "status": "PENDING",
        "current_index": 0,
        "created_at": now_s,
        "expiresAt": exp_s,  # TTL attribute
    }
    _table.put_item(Item=item)

    return {
        "offerId": offer_id,
        "pnrId": pnr_id,
        "passenger": passenger,
        "link": link,
        "status": "PENDING",
        "hasOptions": bool(options),
    }
