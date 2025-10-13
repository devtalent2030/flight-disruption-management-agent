import os, json, hashlib, time, boto3
ddb = boto3.resource("dynamodb")
table = ddb.Table(os.getenv("OFFERS_TABLE","Offers"))

def _get_by_token(token):
    th = hashlib.sha256(token.encode()).hexdigest()
    # Demo: scan; real impl uses GSI on token_hash
    resp = table.scan(FilterExpression="token_hash = :t", ExpressionAttributeValues={":t": th})
    items = resp.get("Items", [])
    return items[0] if items else None

def handler(event, context):
    token = event["pathParameters"]["token"]
    route = event["requestContext"]["http"]["method"] + " " + event["requestContext"]["http"]["path"]
    offer = _get_by_token(token)
    if not offer or offer["expires_at"] < int(time.time()):
        return _res(410, {"status":"expired"})

    if event["requestContext"]["http"]["method"] == "GET":
        o = offer["options"][offer["current_index"]]
        remaining = max(0, len(offer["options"]) - offer["current_index"] - 1)
        return _res(200, {"option":o, "expiresAt": offer["expires_at"], "remaining": remaining, "status":"pending"})

    if route.endswith("/accept"):
        table.update_item(
            Key={"offer_id": offer["offer_id"]},
            UpdateExpression="SET #s = :c",
            ConditionExpression="#s = :p",
            ExpressionAttributeNames={"#s":"state"},
            ExpressionAttributeValues={":c":"ACCEPTED",":p":"PENDING"},
        )
        return _res(200, {"confirmation":{"flightNo": offer["options"][offer["current_index"]]["flightNo"]}})

    if route.endswith("/next"):
        next_idx = offer["current_index"] + 1
        if next_idx >= len(offer["options"]): return _res(410, {"message":"no more options"})
        table.update_item(Key={"offer_id": offer["offer_id"]},
                          UpdateExpression="SET current_index = :i",
                          ExpressionAttributeValues={":i": next_idx})
        o = offer["options"][next_idx]
        remaining = len(offer["options"]) - next_idx - 1
        return _res(200, {"option": o, "remaining": remaining})

    if route.endswith("/decline"):
        table.update_item(Key={"offer_id": offer["offer_id"]},
                          UpdateExpression="SET #s = :d",
                          ExpressionAttributeNames={"#s":"state"},
                          ExpressionAttributeValues={":d":"DECLINED"})
        return _res(200, {"voucher":{"code":"DEMO-150","amount":150,"expiry":"2025-12-31"}})

    return _res(400, {"message":"unsupported"})
def _res(code, body): return {"statusCode": code, "headers":{"Content-Type":"application/json"}, "body": json.dumps(body)}
