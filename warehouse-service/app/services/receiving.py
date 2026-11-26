from fastapi import HTTPException

from app.clients.catalog_client import bins, home_warehouse
from app.clients.identity_client import Caller
from app.database import Database
from app.models import GRN, GRNItem, Movement, POStatus
from app.schemas import GRNCreate
from app.services.purchase_orders import warehouse_order
from app.services.stock import lock_balances, write_movement


def receive_goods(body: GRNCreate, db: Database, clerk: Caller):
    warehouse = home_warehouse(clerk)
    bin_ids = {line.bin_id for line in body.items}
    bins(bin_ids, warehouse_id=warehouse["id"])
    order = warehouse_order(db, body.po_id, warehouse["id"], lock=True)
    if order.status not in (POStatus.OPEN.value, POStatus.PARTIAL.value):
        raise HTTPException(409, "This purchase order is closed to receipts.")
    po_items = {line.id: line for line in order.items}
    if len({line.po_item_id for line in body.items}) != len(body.items):
        raise HTTPException(422, "Include each purchase order line once per receipt.")
    for line in body.items:
        po_item = po_items.get(line.po_item_id)
        if po_item is None:
            raise HTTPException(422, "Use lines from this purchase order.")
        if line.qty > po_item.outstanding_qty:
            raise HTTPException(409, "Receipt quantity exceeds the outstanding purchase order quantity.")

    receipt = GRN(
        grn_no=body.grn_no.strip().upper(),
        po_id=order.id,
        received_by=clerk.id,
        remark=body.remark,
    )
    db.add(receipt)
    db.flush()
    keys = [(warehouse["id"], po_items[line.po_item_id].product_id) for line in body.items]
    balances = lock_balances(db, keys)
    for line in body.items:
        po_item = po_items[line.po_item_id]
        po_item.received_qty += line.qty
        receipt.items.append(
            GRNItem(
                po_item_id=po_item.id,
                product_id=po_item.product_id,
                qty=line.qty,
                bin_id=line.bin_id,
            )
        )
        write_movement(
            db,
            balances[(warehouse["id"], po_item.product_id)],
            Movement.RECEIPT,
            line.qty,
            "GRN",
            str(receipt.id),
            clerk.id,
        )
    order.status = (
        POStatus.CLOSED.value
        if all(line.outstanding_qty == 0 for line in order.items)
        else POStatus.PARTIAL.value
    )
    db.commit()
    db.refresh(receipt)
    return receipt
