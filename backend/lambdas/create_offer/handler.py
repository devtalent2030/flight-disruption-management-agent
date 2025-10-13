import os, time, json, hashlib, uuid, boto3
ddb = boto3.resource("dynamodb")
table = ddb.Table(os.getenv("OFFERS_TABLE","Offers"))

def handler(event, context):
    pnr = event["impacted"][0]  # demo 1 PNR
    options = event["options"]
    offer_id = str(uuid.uuid4())
    expires_at = int(time.time()) + 30*60  # 30m
    token = str(uuid.uuid4())
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    item = {
        "offer_id": offer_id, "pnr_id": pnr["pnr_id"], "state": "PENDING",
        "options": options, "current_index": 0,
        "expires_at": expires_at, "token_hash": token_hash,
    }
    table.put_item(Item=item)
    return {"offer_id": offer_id, "token": token, "expires_at": expires_at}
