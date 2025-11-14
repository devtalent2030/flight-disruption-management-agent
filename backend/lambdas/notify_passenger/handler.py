import os

import boto3

_sns = boto3.client("sns")


def handler(event, _context):
    """
    Expects:
    {
      "link":"https://example.com/offer?...",
      "passenger":{"email":"..."}
    }
    """
    link = event.get("link", "")
    email = (event.get("passenger") or {}).get("email", "")
    msg = f"Your flight changed. Review options: {link}"

    topic = os.getenv("ALERT_TOPIC_ARN")
    if topic:
        _sns.publish(TopicArn=topic, Message=msg, Subject="FDMA Offer")

    # MOCK mode: just log-like payload back
    return {"notified": True, "email": email, "link": link}
