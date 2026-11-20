from datetime import date, timedelta
from decimal import Decimal

from tests.helpers import adjustment, open_order, receipt_body, stock, today


def test_multi_line_po_partial_full_and_over_receipt(client, sample):
    manager, clerk = sample.auth("manager"), sample.auth("clerk")
    items = [
        {"product_id": sample.product.id, "ordered_qty": "10", "unit_price": "2.50"},
        {"product_id": sample.other_product.id, "ordered_qty": "2", "unit_price": "1.20"},
    ]
    order = open_order(client, sample, items)
    assert order["status"] == "OPEN"
    assert order["total_amount"] == "27.40"
    assert order["warehouse_id"] == sample.home.id
    path = f"/purchase-orders/{order['id']}"

    body = receipt_body(sample, order)
    invalid_bin = {**body, "items": [{**body["items"][0], "bin_id": sample.away_bin.id}]}
    assert client.post("/grns", headers=clerk, json=invalid_bin).status_code == 422
    assert client.post("/grns", headers=clerk, json={**body, "warehouse_id": sample.away.id}).status_code == 422
    assert client.post("/grns", headers=sample.auth("away_clerk"), json=body).status_code == 404
    assert client.get(path, headers=sample.auth("away_manager")).status_code == 404
    assert client.post("/grns", headers=manager, json=body).status_code == 403

    posted = client.post("/grns", headers=clerk, json=body)
    assert posted.status_code == 201, posted.text
    assert posted.json()["received_by"] == sample.clerk.id
    assert stock(client, sample) == 4
    partial = client.get(path, headers=manager).json()
    assert partial["status"] == "PARTIAL"
    assert Decimal(partial["items"][0]["outstanding_qty"]) == 6
    assert client.patch(path + "/cancel", headers=manager).status_code == 409
    filtered = client.get("/purchase-orders", headers=manager, params={"status": "PARTIAL", "supplier_id": sample.supplier.id})
    assert [row["id"] for row in filtered.json()["items"]] == [order["id"]]
    assert client.get("/purchase-orders", headers=sample.auth("away_manager")).json()["total"] == 0

    over = client.post("/grns", headers=clerk, json=receipt_body(sample, order, "7", "GRN-OVER"))
    assert over.status_code == 409 and stock(client, sample) == 4
    assert client.get(path, headers=clerk).json()["items"][0]["received_qty"] == "4.000"

    remaining = receipt_body(sample, order, "6", "GRN-2")
    remaining["items"].extend(receipt_body(sample, order, "2", item=1)["items"])
    assert client.post("/grns", headers=clerk, json=remaining).status_code == 201
    closed = client.get(path, headers=manager).json()
    assert closed["status"] == "CLOSED"
    assert all(Decimal(line["outstanding_qty"]) == 0 for line in closed["items"])
    assert stock(client, sample) == 10
    assert stock(client, sample, product=sample.other_product) == 2
    assert client.post("/grns", headers=clerk, json=body).status_code == 409
    history = client.get("/stock/ledger", headers=clerk, params={"product_id": sample.product.id}).json()["items"]
    assert {row["movement_type"] for row in history} == {"RECEIPT"}
    assert {row["created_by"] for row in history} == {sample.clerk.id}
    assert len(history) == 2


def test_po_close_cancel_and_validation(client, sample):
    manager, clerk = sample.auth("manager"), sample.auth("clerk")
    created = open_order(client, sample)
    url = f"/purchase-orders/{created['id']}"
    assert client.patch(url + "/close", headers=clerk).status_code == 403
    assert client.patch(url + "/close", headers=manager).json()["status"] == "CLOSED"
    assert client.patch(url + "/close", headers=manager).status_code == 200
    assert client.patch(url + "/cancel", headers=manager).status_code == 409

    second = open_order(client, sample, number="PO-2")
    another = f"/purchase-orders/{second['id']}"
    assert client.patch(another + "/cancel", headers=manager).json()["status"] == "CANCELLED"
    assert client.post("/grns", headers=clerk, json=receipt_body(sample, second)).status_code == 409

    line = {"product_id": sample.product.id, "ordered_qty": "1", "unit_price": "3.00"}
    body = {"po_no": sample.prefix + "-PO-3", "supplier_id": sample.supplier.id,
            "ordered_on": today(), "items": [line, line]}
    assert client.post("/purchase-orders", headers=manager, json=body).status_code == 422
    assert client.post("/purchase-orders", headers=clerk, json=body).status_code == 403
    assert client.post("/purchase-orders", headers=manager, json={
        **body, "items": [{**line, "product_id": 2_000_000}],
    }).status_code == 422


def test_issue_adjust_and_transfer_roles_and_balances(client, sample):
    manager, clerk = sample.auth("manager"), sample.auth("clerk")
    count = {"product_id": sample.product.id, "counted_quantity": "5", "reason": "   "}
    assert client.post("/stock/adjust", headers=manager, json=count).status_code == 422
    assert client.post("/stock/adjust", headers=clerk, json={
        **count, "reason": "Count",
    }).status_code == 403
    start = adjustment(client, sample, "5")
    assert start["movement_type"] == "ADJUSTMENT" and start["created_by"] == sample.manager.id
    assert client.post("/stock/adjust", headers=manager, json={**count, "reason": "Again"}).status_code == 409

    issue = {"product_id": sample.product.id, "quantity": "2.125", "requisition_no": "REQ-1"}
    assert client.post("/stock/issue", headers=clerk, json={**issue, "warehouse_id": sample.away.id}).status_code == 422
    assert client.post("/stock/issue", headers=manager, json=issue).status_code == 403
    assert client.post("/stock/issue", headers=sample.auth("away_clerk"), json=issue).status_code == 409
    assert client.post("/stock/issue", headers=clerk, json={**issue, "quantity": "10"}).status_code == 409
    item = client.post("/stock/issue", headers=clerk, json=issue)
    assert item.status_code == 201
    assert item.json()["created_by"] == sample.clerk.id
    assert item.json()["reference_id"] == "REQ-1"
    assert stock(client, sample) == Decimal("2.875")

    transfer = {"product_id": sample.product.id, "source_warehouse_id": sample.home.id,
                "destination_warehouse_id": sample.away.id, "quantity": "1.500"}
    assert client.post("/stock/transfer", headers=clerk, json=transfer).status_code == 403
    assert client.post("/stock/transfer", headers=sample.auth("away_manager"), json=transfer).status_code == 403
    assert client.post("/stock/transfer", headers=manager, json={
        **transfer, "destination_warehouse_id": sample.home.id,
    }).status_code == 422
    assert client.post("/stock/transfer", headers=manager, json={**transfer, "quantity": "100"}).status_code == 409
    move = client.post("/stock/transfer", headers=manager, json=transfer)
    assert move.status_code == 201, move.text
    ledger = move.json()
    assert ledger["out"]["movement_type"] == "TRANSFER_OUT"
    assert ledger["incoming"]["movement_type"] == "TRANSFER_IN"
    assert ledger["out"]["reference_id"] == ledger["incoming"]["reference_id"] == ledger["reference_id"]
    assert ledger["out"]["created_by"] == ledger["incoming"]["created_by"] == sample.manager.id
    assert stock(client, sample) == Decimal("1.375")
    assert stock(client, sample, warehouse=sample.away) == Decimal("1.500")
    assert len(client.get("/stock/balance", headers=clerk, params={
        "product_id": sample.product.id,
    }).json()["items"]) >= 2
    path = "/stock/ledger"
    params = {"product_id": sample.product.id, "from": today(), "to": today(), "size": 2}
    assert client.get(path, headers=clerk, params=params).json()["total"] == 4
    assert len(client.get(path, headers=clerk, params={**params, "page": 2}).json()["items"]) == 2
    assert client.get(path, headers=clerk, params={
        **params, "warehouse_id": sample.home.id,
    }).json()["total"] == 3
    assert client.get(path, headers=clerk, params={**params, "from": "2099-01-01"}).status_code == 422
    assert client.delete(path, headers=manager).status_code == 405


def test_reorder_expiry_valuation_and_movement_analysis(client, sample):
    manager, clerk, admin = sample.auth("manager"), sample.auth("clerk"), sample.auth("admin")
    url = f"/stock/expiry/{sample.product.id}"
    past = (date.fromisoformat(today()) - timedelta(days=1)).isoformat()
    assert client.put(url, headers=manager, json={"expiry_on": past}).status_code == 409

    adjustment(client, sample, "26")
    adjustment(client, sample, "2", sample.other_product)
    issues = {"product_id": sample.product.id, "quantity": "22", "requisition_no": "REQ-REPORT"}
    assert client.post("/stock/issue", headers=clerk, json=issues).status_code == 201
    assert client.put(url, headers=manager, json={"expiry_on": past}).status_code == 200
    alerts = client.get("/alerts/reorder", headers=manager).json()
    row = next(item for item in alerts if item["product_id"] == sample.product.id)
    assert Decimal(row["quantity"]) == 4 and Decimal(row["reorder_level"]) == 5
    assert client.get("/alerts/reorder", headers=clerk).status_code == 403
    expiring = client.get("/alerts/expiry", headers=manager).json()
    assert next(item for item in expiring if item["product_id"] == sample.product.id)["status"] == "EXPIRED"
    assert client.put(url, headers=manager, json={"expiry_on": today()}).status_code == 200
    expiring = client.get("/alerts/expiry", headers=manager).json()
    assert next(item for item in expiring if item["product_id"] == sample.product.id)["status"] == "EXPIRING"
    assert client.put(url, headers=manager, json={"expiry_on": None}).status_code == 200
    assert client.get("/alerts/expiry", headers=manager).json() == []

    values = client.get("/reports/valuation", headers=admin)
    assert values.status_code == 200, values.text
    assert next(item for item in values.json() if item["warehouse_id"] == sample.home.id)["value"] == "12.40"
    assert client.get("/reports/valuation", headers=manager).status_code == 403
    path = "/reports/movement-analysis"
    params = {"from": today(), "to": today()}
    values = client.get(path, headers=admin, params=params)
    assert values.status_code == 200, values.text
    data = {row["product_id"]: row for row in values.json()}
    assert data[sample.product.id]["classification"] == "FAST"
    assert Decimal(data[sample.product.id]["issued_quantity"]) == 22
    assert data[sample.other_product.id]["classification"] == "SLOW"
    assert client.get(path, headers=admin, params={**params, "to": past}).status_code == 422
    assert client.get(path, headers=clerk, params=params).status_code == 403
