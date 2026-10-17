"""Minimal KabadiLink pickup API for an unauthenticated prototype.

IMPORTANT: this is demo-only until authentication/authorization is added.
The client-supplied actor IDs are not proof of identity.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

TABLE_NAME = os.environ["PICKUPS_TABLE"]
ddb = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)
SLOTS = {"8–10 AM", "10 AM–12 PM", "4–6 PM"}
CATEGORIES = ("plastic", "wet", "ewaste")
VALID_STATUSES = {"Requested", "Accepted", "On the way", "Weighed", "Paid", "Cancelled"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def response(status: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(body, default=json_default),
    }


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def read_body(event: dict[str, Any]) -> dict[str, Any]:
    try:
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode("utf-8")
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (json.JSONDecodeError, ValueError, TypeError):
        raise ApiError(400, "Request body must be a JSON object.")


class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def get_path(event: dict[str, Any]) -> str:
    return event.get("rawPath") or event.get("path") or "/"


def get_method(event: dict[str, Any]) -> str:
    return (event.get("requestContext", {}).get("http", {}).get("method")
            or event.get("httpMethod") or "GET").upper()


def validate_kg(value: Any, required: bool = True) -> dict[str, float]:
    if not isinstance(value, dict):
        raise ApiError(400, "kg must contain plastic, wet, and ewaste values.")
    result: dict[str, float] = {}
    for category in CATEGORIES:
        raw = value.get(category, 0)
        try:
            kg = float(raw)
        except (TypeError, ValueError):
            raise ApiError(400, f"{category} must be a number.")
        if kg < 0 or kg > 1000:
            raise ApiError(400, f"{category} must be between 0 and 1000 kg.")
        result[category] = kg
    if required and sum(result.values()) <= 0:
        raise ApiError(400, "Enter a positive weight for at least one material.")
    return result


def create_pickup(body: dict[str, Any]) -> dict[str, Any]:
    hid = str(body.get("hid", "")).strip()
    pickup_date = str(body.get("date", "")).strip()
    slot = str(body.get("slot", "")).strip()
    address = str(body.get("address", "")).strip()
    note = str(body.get("note", "")).strip()
    if not hid:
        raise ApiError(400, "hid is required for the demo household.")
    try:
        parsed_date = date.fromisoformat(pickup_date)
    except ValueError:
        raise ApiError(400, "date must use YYYY-MM-DD format.")
    if parsed_date < date.today():
        raise ApiError(400, "Pickup date must be today or later.")
    if slot not in SLOTS:
        raise ApiError(400, "Choose a valid pickup time slot.")
    if not address:
        raise ApiError(400, "address is required.")
    if len(address) > 500 or len(note) > 1000:
        raise ApiError(400, "Address or note is too long.")
    kg = validate_kg(body.get("kg", {}))
    if kg["wet"] > float(os.getenv("WET_DAILY_CAP_KG", "10")):
        raise ApiError(400, "Wet waste exceeds the daily limit of 10 kg.")

    created = now_iso()
    item = {
        "id": "KL-" + uuid.uuid4().hex[:10].upper(),
        "hid": hid,
        "date": pickup_date,
        "slot": slot,
        "address": address,
        "note": note,
        "est": kg,
        "status": "Requested",
        "events": [{"s": "Requested", "at": created, "by": hid}],
        "createdAt": created,
    }
    table.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
    return item


def list_pickups(params: dict[str, str]) -> list[dict[str, Any]]:
    household_id = params.get("householdId") or params.get("hid")
    collector_id = params.get("collectorId") or params.get("cid")
    status = params.get("status")
    if household_id:
        result = table.query(IndexName="household-date-index", KeyConditionExpression=Key("hid").eq(household_id), ScanIndexForward=False)
        items = result.get("Items", [])
    elif collector_id:
        result = table.query(IndexName="collector-date-index", KeyConditionExpression=Key("cid").eq(collector_id), ScanIndexForward=False)
        items = result.get("Items", [])
    elif status:
        if status not in VALID_STATUSES:
            raise ApiError(400, "Unknown pickup status.")
        result = table.query(IndexName="status-date-index", KeyConditionExpression=Key("status").eq(status), ScanIndexForward=False)
        items = result.get("Items", [])
    else:
        # Convenient for the small prototype. Add pagination and narrower queries before production.
        items = table.scan(Limit=100).get("Items", [])
    if status and (household_id or collector_id):
        items = [item for item in items if item.get("status") == status]
    return sorted(items, key=lambda item: (item.get("date", ""), item.get("createdAt", "")), reverse=True)


def get_pickup(pickup_id: str) -> dict[str, Any]:
    result = table.get_item(Key={"id": pickup_id})
    item = result.get("Item")
    if not item:
        raise ApiError(404, "Pickup not found.")
    return item


def update_status(pickup_id: str, body: dict[str, Any]) -> dict[str, Any]:
    new_status = str(body.get("status", "")).strip()
    actor_id = str(body.get("actorId", "")).strip()
    if new_status not in {"Accepted", "On the way", "Cancelled"}:
        raise ApiError(400, "Allowed status updates are Accepted, On the way, or Cancelled.")
    if not actor_id:
        raise ApiError(400, "actorId is required for this demo action.")
    item = get_pickup(pickup_id)
    old_status = item["status"]
    cid = item.get("cid")
    if new_status == "Accepted":
        if old_status != "Requested":
            raise ApiError(409, "This pickup is no longer available to accept.")
        cid = actor_id
    elif new_status == "On the way":
        if old_status != "Accepted" or cid != actor_id:
            raise ApiError(409, "Only the assigned collector can mark an accepted pickup as on the way.")
    elif new_status == "Cancelled":
        if old_status not in {"Requested", "Accepted"}:
            raise ApiError(409, "This pickup can no longer be cancelled.")
        if item.get("hid") != actor_id:
            raise ApiError(403, "Only the requesting household can cancel this pickup.")

    timestamp = now_iso()
    try:
        values: dict[str, Any] = {":new": new_status, ":old": old_status, ":event": {"s": new_status, "at": timestamp, "by": actor_id}}
        update_expr = "SET #status = :new, events = list_append(if_not_exists(events, :empty), :eventList)"
        values[":empty"] = []
        values[":eventList"] = [values.pop(":event")]
        names = {"#status": "status"}
        if new_status == "Accepted":
            update_expr += ", cid = :cid"
            values[":cid"] = cid
        table.update_item(
            Key={"id": pickup_id},
            UpdateExpression=update_expr,
            ConditionExpression="#status = :old",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise ApiError(409, "Pickup status changed. Refresh and try again.")
        raise
    return get_pickup(pickup_id)


def record_weigh_in(pickup_id: str, body: dict[str, Any]) -> dict[str, Any]:
    actor_id = str(body.get("collectorId", "")).strip()
    if not actor_id:
        raise ApiError(400, "collectorId is required for this demo action.")
    kg = validate_kg(body.get("kg", {}))
    item = get_pickup(pickup_id)
    if item.get("cid") != actor_id:
        raise ApiError(403, "This pickup is not assigned to that collector.")
    if item.get("status") != "On the way":
        raise ApiError(409, "Mark the pickup as on the way before weighing it.")
    wet_cap = float(os.getenv("WET_DAILY_CAP_KG", "10"))
    if kg["wet"] > wet_cap:
        raise ApiError(400, f"Wet waste cannot exceed {wet_cap:g} kg per pickup in this prototype.")

    rates = {
        "plastic": float(os.getenv("PLASTIC_RATE", "14")),
        "wet": 0.0,
        "ewaste": float(os.getenv("EWASTE_RATE", "40")),
    }
    points_per_kg = {
        "plastic": float(os.getenv("PLASTIC_POINTS_PER_KG", "10")),
        "wet": float(os.getenv("WET_POINTS_PER_KG", "2")),
        "ewaste": float(os.getenv("EWASTE_POINTS_PER_KG", "20")),
    }
    cash = {category: round(kg[category] * rates[category], 2) for category in CATEGORIES}
    points = {category: round(kg[category] * points_per_kg[category]) for category in CATEGORIES}
    payout = {
        "kg": kg,
        "cash": cash,
        "cashTotal": round(sum(cash.values()), 2),
        "points": points,
        "totalPoints": sum(points.values()),
        "rates": rates,
        "pointsPerKg": points_per_kg,
    }
    timestamp = now_iso()
    try:
        table.update_item(
            Key={"id": pickup_id},
            UpdateExpression="SET act = :act, payout = :payout, #status = :paid, events = list_append(if_not_exists(events, :empty), :events)",
            ConditionExpression="#status = :expected AND cid = :cid AND attribute_not_exists(payout)",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":act": kg,
                ":payout": payout,
                ":paid": "Paid",
                ":expected": "On the way",
                ":cid": actor_id,
                ":empty": [],
                ":events": [
                    {"s": "Weighed", "at": timestamp, "by": actor_id},
                    {"s": "Paid", "at": timestamp, "by": actor_id},
                ],
            },
        )
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise ApiError(409, "Weigh-in already recorded or pickup status changed.")
        raise
    return get_pickup(pickup_id)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        method = get_method(event)
        path = get_path(event).rstrip("/") or "/"
        params = event.get("queryStringParameters") or {}
        path_params = event.get("pathParameters") or {}
        if method == "GET" and path == "/pickups":
            return response(200, {"items": list_pickups(params)})
        if method == "POST" and path == "/pickups":
            item = create_pickup(read_body(event))
            return response(201, item)
        if method == "GET" and path.startswith("/pickups/"):
            pickup_id = path_params.get("id") or path.split("/")[2]
            return response(200, get_pickup(pickup_id))
        if method == "PATCH" and path.endswith("/status"):
            pickup_id = path_params.get("id") or path.split("/")[2]
            return response(200, update_status(pickup_id, read_body(event)))
        if method == "PATCH" and path.endswith("/weigh-in"):
            pickup_id = path_params.get("id") or path.split("/")[2]
            return response(200, record_weigh_in(pickup_id, read_body(event)))
        return response(404, {"error": "Route not found."})
    except ApiError as error:
        return response(error.status_code, {"error": error.message})
    except Exception:
        # Do not expose internal errors to clients. CloudWatch logs can be used for debugging.
        print("Unhandled backend error", {"path": get_path(event), "method": get_method(event)})
        return response(500, {"error": "Internal server error."})
