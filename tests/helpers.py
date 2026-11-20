from datetime import datetime, timezone
from decimal import Decimal


def today():
    return datetime.now(timezone.utc).date().isoformat()


def open_order(client, sample, items=None, number="PO-1"):
    if items is None:
        items = [{"product_id": sample.product.id, "ordered_qty": "10", "unit_price": "2.50"}]
    response = client.post("/purchase-orders", headers=sample.auth("manager"), json={
        "po_no": sample.prefix + "-" + number,
        "supplier_id": sample.supplier.id,
        "ordered_on": today(),
        "items": items,
    })
    assert response.status_code == 201, response.text
    return response.json()


def receipt_body(sample, order, qty="4", number="GRN-1", item=0):
    return {
        "grn_no": sample.prefix + "-" + number,
        "po_id": order["id"],
        "items": [{"po_item_id": order["items"][item]["id"], "qty": qty, "bin_id": sample.bin.id}],
    }


def adjustment(client, sample, qty, product=None):
    response = client.post("/stock/adjust", headers=sample.auth("manager"), json={
        "product_id": (product or sample.product).id, "counted_quantity": qty, "reason": "Physical count",
    })
    assert response.status_code == 201, response.text
    return response.json()


def stock(client, sample, warehouse=None, product=None):
    response = client.get("/stock/balance", headers=sample.auth("admin"), params={
        "product_id": (product or sample.product).id,
        "warehouse_id": (warehouse or sample.home).id,
    })
    assert response.status_code == 200, response.text
    return Decimal(response.json()["items"][0]["quantity"])
