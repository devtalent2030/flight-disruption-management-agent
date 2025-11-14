"""
Notification helper.

Supports two channels controlled by env NOTIFY_CHANNEL:
- "SES": send via Amazon SES (requires SES_FROM_EMAIL verified).
- "MOCK": log-only, no external call (default).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import boto3


class Notifier:
    def __init__(self) -> None:
        self.channel = os.getenv("NOTIFY_CHANNEL", "MOCK").upper()
        self.ses_from = os.getenv("SES_FROM_EMAIL", "")
        self._ses = boto3.client("ses") if self.channel == "SES" else None

    def send(self, to_email: str, subject: str, body_html: str, body_text: str) -> Dict[str, Any]:
        """
        Send a notification.

        Args:
            to_email: Recipient email.
            subject: Email subject.
            body_html: HTML body.
            body_text: Plain-text body.

        Returns:
            dict with a MessageId (MOCK returns a synthetic id).
        """
        if not to_email:
            raise ValueError("to_email is required")
        if not subject:
            raise ValueError("subject is required")

        if self.channel == "SES":
            if not self.ses_from:
                raise RuntimeError("SES_FROM_EMAIL not set (required for SES channel)")
            resp = self._ses.send_email(  # type: ignore[union-attr]
                Source=self.ses_from,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": body_text, "Charset": "UTF-8"},
                        "Html": {"Data": body_html, "Charset": "UTF-8"},
                    },
                },
            )
            return {"MessageId": resp.get("MessageId", "SES-unknown")}

        # MOCK channel: log-only
        print(f"[MOCK EMAIL] to={to_email}\nSubject: {subject}\n\n{body_text}\n")
        return {"MessageId": f"MOCK-{to_email}"}
