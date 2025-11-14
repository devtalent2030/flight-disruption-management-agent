from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import boto3

from common.notifier import Notifier

dynamodb = boto3.client("dynamodb")

EVENTS_TABLE = os.getenv("EVENTS_TABLE", "Events")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    has_options = event.get("hasOptions", False)
    if not has_options:
        return {**event, "notified": False, "reason": "NO_OPTIONS"}

    passenger = event.get("passenger") or {}
    to_email = passenger.get("email")
    link = event.get("link")

    if not to_email or not link:
        return {**event, "notified": False, "reason": "MISSING_CONTACT_OR_LINK"}

    subject = "Your rebooking options are ready"
    body_text = (
        "Hello,\n\nWe’ve found new options for your disrupted flight."
        f"\n\nReview & respond: {link}\n\nThis link will expire automatically."
    )
    body_html = f"""
    <html>
      <body style="font-family:Arial,Helvetica,sans-serif;">
        <p>Hello,</p>
        <p>We’ve found new options for your disrupted flight.</p>
        <p><a href="{link}">Review & respond</a> (link expires automatically)</p>
        <p>Thank you.</p>
      </body>
    </html>
    """

    notifier = Notifier()
    resp = notifier.send(to_email, subject, body_html, body_text)
    print("Notifier response:", resp)

    # Audit event
    event_id = "EVT-" + str(uuid.uuid4())
    dynamodb.put_item(
        TableName=EVENTS_TABLE,
        Item={
            "eventId": {"S": event_id},
            "type": {"S": "OFFER_NOTIFIED"},
            "entityId": {"S": event.get("offerId", "")},
            "payload": {"M": {"email": {"S": to_email}}},
            "createdAt": {"S": _iso_now()},
        },
    )

    return {**event, "notified": True}
