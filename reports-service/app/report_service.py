from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException

from app.clients.catalog_client import active_warehouse, products, warehouses
from app.clients.identity_client import Caller
from app.clients.warehouse_client import balances, issue_totals
from app.config import get_settings


def home_warehouse(user: Caller) -> int:
    if user.warehouse_id is None:
        raise HTTPException(403, "An active home warehouse is required.")
    return active_warehouse(user.warehouse_id)["id"]


def reorder(user: Caller) -> list[dict]:
    warehouse_id = home_warehouse(user)
    catalog_products = products(active_only=True)
    balances_by_product = {
        row["product_id"]: row for row in balances(warehouse_id=warehouse_id)
    }
    rows = []
    for product in catalog_products:
        balance = balances_by_product.get(product["id"])
        quantity = Decimal(str(balance["quantity"])) if balance else Decimal("0")
        if quantity < Decimal(product["reorder_level"]):
            rows.append(
                {
                    "product_id": product["id"],
                    "sku": product["sku"],
                    "name": product["name"],
                    "quantity": quantity,
                    "reorder_level": Decimal(str(product["reorder_level"])),
                }
            )
    return sorted(rows, key=lambda row: row["sku"])


def expiry_alerts(user: Caller) -> list[dict]:
    warehouse_id = home_warehouse(user)
    today = datetime.now(timezone.utc).date()
    cutoff = today + timedelta(days=get_settings().expiry_days)
    product_map = {row["id"]: row for row in products(active_only=False)}
    rows = []
    for balance in balances(warehouse_id=warehouse_id):
        expiry_value = balance["expiry_on"]
        if not expiry_value or Decimal(str(balance["quantity"])) <= 0:
            continue
        expiry_on = date.fromisoformat(expiry_value) if isinstance(expiry_value, str) else expiry_value
        if expiry_on > cutoff:
            continue
        product = product_map.get(balance["product_id"])
        if product is None:
            raise HTTPException(503, "Catalog is missing a referenced product.")
        rows.append(
            {
                "product_id": product["id"],
                "sku": product["sku"],
                "name": product["name"],
                "quantity": Decimal(str(balance["quantity"])),
                "expiry_on": expiry_on,
                "status": "EXPIRED" if expiry_on < today else "EXPIRING",
            }
        )
    return sorted(rows, key=lambda row: (row["expiry_on"], row["sku"]))


def valuation() -> list[dict]:
    product_map = {row["id"]: row for row in products(active_only=False)}
    location_rows = warehouses()
    totals = {row["id"]: Decimal("0") for row in location_rows}
    for balance in balances():
        product = product_map.get(balance["product_id"])
        if product is None or balance["warehouse_id"] not in totals:
            raise HTTPException(503, "Catalog is missing a warehouse or product referenced by stock.")
        totals[balance["warehouse_id"]] += (
            Decimal(str(balance["quantity"])) * Decimal(str(product["unit_cost"]))
        )
    result = []
    for location in location_rows:
        result.append(
            {
                "warehouse_id": location["id"],
                "warehouse_code": location["code"],
                "warehouse_name": location["name"],
                "value": totals[location["id"]].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            }
        )
    return sorted(result, key=lambda row: row["warehouse_code"])


def movement_analysis(start: date, end: date) -> list[dict]:
    if start > end:
        raise HTTPException(422, "The start date must be on or before the end date.")
    settings = get_settings()
    issued = issue_totals(start, end)
    catalog_products = products(active_only=False)
    rows = []
    for product in catalog_products:
        amount = Decimal(str(issued.get(product["id"], 0)))
        if product["is_deleted"] and product["id"] not in issued:
            continue
        classification = (
            "FAST" if amount >= settings.fast_units
            else "SLOW" if amount <= settings.slow_units
            else "MEDIUM"
        )
        rows.append(
            {
                "product_id": product["id"],
                "sku": product["sku"],
                "name": product["name"],
                "issued_quantity": amount,
                "classification": classification,
            }
        )
    return sorted(rows, key=lambda row: (-row["issued_quantity"], row["sku"]))
