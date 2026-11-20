from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db import get_engine
from app.main import app
from app.routers import inbound, inventory

from tests.helpers import adjustment, open_order, receipt_body, stock


def overlap(monkeypatch, module, first_request, second_request):
    flushed = Event()
    release = Event()
    leader_pids = []
    original = module.write_movement

    def hold_first(db, *args, **kwargs):
        entry = original(db, *args, **kwargs)
        if not flushed.is_set():
            leader_pids.append(db.scalar(text("SELECT pg_backend_pid()")))
            flushed.set()
            if not release.wait(10):
                raise AssertionError("The test did not release the first transaction.")
        return entry

    monkeypatch.setattr(module, "write_movement", hold_first)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_request)
        try:
            assert flushed.wait(5), "The first PostgreSQL write did not flush."
            second = pool.submit(second_request)
            with get_engine().connect().execution_options(isolation_level="AUTOCOMMIT") as observer:
                deadline = monotonic() + 5
                while monotonic() < deadline:
                    blocked = observer.scalar(text("""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_stat_activity
                            WHERE datname = current_database()
                              AND :leader = ANY(pg_blocking_pids(pid))
                        )
                    """), {"leader": leader_pids[0]})
                    if blocked:
                        break
                    sleep(0.02)
                else:
                    pytest.fail("A second PostgreSQL connection did not wait for the first.")
        finally:
            release.set()
        return first.result(10), second.result(10)


def test_issue_the_last_unit_twice(client, sample, monkeypatch):
    adjustment(client, sample, "1")
    clerk = sample.auth("clerk")

    def issue(number):
        return client.post("/stock/issue", headers=clerk, json={
            "product_id": sample.product.id, "quantity": "1", "requisition_no": number,
        })

    first, second = overlap(monkeypatch, inventory, lambda: issue("REQ-1"), lambda: issue("REQ-2"))
    assert [first.status_code, second.status_code] == [201, 409]
    assert second.json()["detail"] == "Insufficient available stock."
    assert stock(client, sample) == 0
    result = client.get("/stock/ledger", headers=clerk, params={"product_id": sample.product.id}).json()
    assert result["total"] == 2
    assert [row["reference_id"] for row in result["items"] if row["movement_type"] == "ISSUE"] == ["REQ-1"]


def test_two_receipts_cannot_consume_same_outstanding_qty(client, sample, monkeypatch):
    order = open_order(client, sample, [{"product_id": sample.product.id, "ordered_qty": "4", "unit_price": "1"}])
    clerk = sample.auth("clerk")

    def receive(number):
        return client.post("/grns", headers=clerk, json=receipt_body(sample, order, "3", number))

    first, second = overlap(monkeypatch, inbound, lambda: receive("GRN-1"), lambda: receive("GRN-2"))
    assert [first.status_code, second.status_code] == [201, 409]
    assert stock(client, sample) == 3
    record = client.get(f"/purchase-orders/{order['id']}", headers=clerk).json()
    assert record["status"] == "PARTIAL"
    assert record["items"][0]["outstanding_qty"] == "1.000"
    with Session(get_engine()) as db:
        assert db.scalar(text("SELECT count(*) FROM grns WHERE po_id = :id"), {"id": order["id"]}) == 1


def test_failure_after_first_transfer_leg_rolls_back(client, sample, monkeypatch):
    adjustment(client, sample, "7")
    manager = sample.auth("manager")
    adjustment(client, sample, "2", sample.other_product)
    # Give the destination a real balance row before comparing both sides.
    response = client.post("/stock/adjust", headers=sample.auth("away_manager"), json={
        "product_id": sample.product.id, "counted_quantity": "3", "reason": "Count at destination",
    })
    assert response.status_code == 201
    original = inventory.write_movement
    flushed = []

    def fail_second(db, balance, movement, *args):
        if movement == "TRANSFER_IN":
            db.execute(text("SELECT 1 / 0"))
        entry = original(db, balance, movement, *args)
        flushed.append(entry.id)
        return entry

    monkeypatch.setattr(inventory, "write_movement", fail_second)
    with TestClient(app, raise_server_exceptions=False) as failing_client:
        result = failing_client.post("/stock/transfer", headers=manager, json={
            "product_id": sample.product.id, "source_warehouse_id": sample.home.id,
            "destination_warehouse_id": sample.away.id, "quantity": "2",
        })
    assert result.status_code == 500
    assert len(flushed) == 1 and flushed[0] is not None
    assert stock(client, sample) == 7
    assert stock(client, sample, warehouse=sample.away) == 3
    history = client.get("/stock/ledger", headers=manager, params={"product_id": sample.product.id}).json()
    assert history["total"] == 2
    assert all(row["movement_type"] == "ADJUSTMENT" for row in history["items"])


def test_every_ledger_row_recomputes_to_its_stored_balance(client, sample):
    adjustment(client, sample, "8")
    assert client.post("/stock/issue", headers=sample.auth("clerk"), json={
        "product_id": sample.product.id, "quantity": "2", "requisition_no": "REQ-1",
    }).status_code == 201
    assert client.post("/stock/transfer", headers=sample.auth("manager"), json={
        "product_id": sample.product.id, "source_warehouse_id": sample.home.id,
        "destination_warehouse_id": sample.away.id, "quantity": "3",
    }).status_code == 201

    with Session(get_engine()) as db:
        running = db.execute(text("""
            SELECT warehouse_id, product_id, position_seq, balance_after,
                SUM(qty_delta) OVER (
                    PARTITION BY warehouse_id, product_id
                    ORDER BY position_seq ROWS UNBOUNDED PRECEDING
                ) AS recomputed
            FROM stock_ledger
            ORDER BY warehouse_id, product_id, position_seq
        """)).mappings()
        last = {}
        for row in running:
            assert row["balance_after"] == row["recomputed"]
            key = (row["warehouse_id"], row["product_id"])
            previous_seq, _ = last.get(key, (0, 0))
            assert row["position_seq"] == previous_seq + 1
            last[key] = row["position_seq"], row["balance_after"]
        current = db.execute(text("SELECT warehouse_id, product_id, position_seq, quantity FROM stock_balances"))
        assert last == {(wh, pid): (seq, qty) for wh, pid, seq, qty in current if seq != 0}


@pytest.mark.parametrize("change", [
    "UPDATE stock_ledger SET balance_after = 0",
    "DELETE FROM stock_ledger",
    "TRUNCATE stock_ledger",
])
def test_database_guards_ledger_and_nonnegative_stock(client, sample, change):
    adjustment(client, sample, "1")
    with Session(get_engine()) as db:
        with pytest.raises(DBAPIError, match="append-only"), db.begin():
            db.execute(text(change))
        with pytest.raises(DBAPIError, match="ck_balance_nonnegative"), db.begin():
            db.execute(text("UPDATE stock_balances SET quantity = -1 WHERE product_id = :product"), {
                "product": sample.product.id,
            })
    assert stock(client, sample) == 1
