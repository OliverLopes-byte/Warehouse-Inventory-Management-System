from fastapi import HTTPException
from sqlalchemy import func, select


def required_row(db, model, row_id: int, label: str):
    row = db.get(model, row_id)
    if row is None:
        raise HTTPException(404, f"{label} not found.")
    return row


def save(db, row, values: dict):
    for field, value in values.items():
        setattr(row, field, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def page_of(db, statement, page: int, size: int):
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    items = db.scalars(statement.offset((page - 1) * size).limit(size)).all()
    return {"items": items, "page": page, "size": size, "total": total}
