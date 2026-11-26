from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.report_service import expiry_alerts, movement_analysis, reorder, valuation
from app.schemas import ExpiryOut, MovementAnalysisOut, ReorderOut, ValuationOut
from app.security import Admin, Manager


router = APIRouter(tags=["Reports"])


@router.get("/alerts/reorder", response_model=list[ReorderOut], tags=["Alerts"])
def get_reorder_alerts(manager: Manager):
    return reorder(manager)


@router.get("/alerts/expiry", response_model=list[ExpiryOut], tags=["Alerts"])
def get_expiry_alerts(manager: Manager):
    return expiry_alerts(manager)


@router.get("/reports/valuation", response_model=list[ValuationOut])
def get_valuation(admin: Admin):
    return valuation()


@router.get("/reports/movement-analysis", response_model=list[MovementAnalysisOut])
def get_movement_analysis(
    admin: Admin,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
):
    return movement_analysis(start, end)
