#!/usr/bin/env python3
"""
Seed minimal demo data into DynamoDB:
- Flights: AB123 (Toronto → Vancouver)
- Passengers: pax001..pax006
- PNRs: PNR-AB123-001..006 (each links a passenger to AB123)

Tables (from SAM template):
  Passengers (pk: passengerId)
  PNRs       (pk: pnrId)
  Flights    (pk: flightNo)
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_REGION", "ca-central-1")

TABLE_FLIGHTS = os.getenv("FLIGHTS_TABLE", "Flights")
TABLE_PASSENGERS = os.getenv("PASSENGERS_TABLE", "Passengers")
TABLE_PNRS = os.getenv("PNRS_TABLE", "PNRs")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
t_flights = dynamodb.Table(TABLE_FLIGHTS)
t_passengers = dynamodb.Table(TABLE_PASSENGERS)
t_pnrs = dynamodb.Table(TABLE_PNRS)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_flights() -> None:
    # Future-ish times for demo
    dep = (datetime.now(timezone.utc) + timedelta(days=7, hours=3)).replace(microsecond=0)
    arr = dep + timedelta(hours=5)
    item = {
        "flightNo": "AB123",
        "origin": "YYZ",       # Toronto
        "destination": "YVR",  # Vancouver
        "scheduledDeparture": dep.isoformat(),
        "scheduledArrival": arr.isoformat(),
        "status": "DISRUPTED",  # so your flow makes sense
        "updatedAt": iso_now(),
    }
    t_flights.put_item(Item=item)
    print(f"Flights: upserted {item['flightNo']}")


def seed_passengers_and_pnrs() -> None:
    # 6 passengers tied to AB123
    pax: List[Dict[str, Any]] = [
        {"passengerId": "pax001", "name": "A. Passenger", "email": "pax001@example.com"},
        {"passengerId": "pax002", "name": "B. Passenger", "email": "pax002@example.com"},
        {"passengerId": "pax003", "name": "C. Passenger", "email": "pax003@example.com"},
        {"passengerId": "pax004", "name": "D. Passenger", "email": "pax004@example.com"},
        {"passengerId": "pax005", "name": "E. Passenger", "email": "pax005@example.com"},
        {"passengerId": "pax006", "name": "F. Passenger", "email": "pax006@example.com"},
    ]

    pnrs: List[Dict[str, Any]] = []
    for i, p in enumerate(pax, start=1):
        pnrs.append({
            "pnrId": f"PNR-AB123-{i:03d}",
            "flightNo": "AB123",
            "passengerId": p["passengerId"],
            "createdAt": iso_now(),
        })

    # Batch write is idempotent here (same keys overwrite with same content)
    with t_passengers.batch_writer(overwrite_by_pkeys=["passengerId"]) as bw:
        for p in pax:
            bw.put_item(Item=p)
    print(f"Passengers: upserted {len(pax)}")

    with t_pnrs.batch_writer(overwrite_by_pkeys=["pnrId"]) as bw:
        for r in pnrs:
            bw.put_item(Item=r)
    print(f"PNRs: upserted {len(pnrs)}")


def main() -> int:
    print(f"Region: {AWS_REGION}")
    print(f"Tables -> Flights: {TABLE_FLIGHTS}, Passengers: {TABLE_PASSENGERS}, PNRs: {TABLE_PNRS}")
    try:
        seed_flights()
        seed_passengers_and_pnrs()
    except ClientError as e:
        print("ERROR:", e, file=sys.stderr)
        return 1
    print("✅ Seeding complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
