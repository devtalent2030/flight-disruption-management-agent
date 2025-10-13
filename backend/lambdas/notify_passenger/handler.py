import os, boto3
sns = boto3.client("sns")
def handler(event, context):
    link = f"{os.getenv('FRONTEND_URL','https://offer.example.com')}?token={event['token']}"
    msg = f"Your flight changed. Review options: {link}"
    topic = os.getenv("ALERT_TOPIC_ARN")
    if topic: sns.publish(TopicArn=topic, Message=msg, Subject="FDMA Offer")
    return {"notified": True, "link": link}
