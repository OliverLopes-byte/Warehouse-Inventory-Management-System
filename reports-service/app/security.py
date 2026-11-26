from typing import Annotated, Callable

from fastapi import Depends, HTTPException

from app.clients.identity_client import Caller, CurrentUser


def require_roles(*allowed: str) -> Callable:
    def check(user: CurrentUser) -> Caller:
        if user.role not in allowed:
            raise HTTPException(403, "Your role cannot perform this action.")
        return user
    return check


Admin = Annotated[Caller, Depends(require_roles("ADMIN"))]
Manager = Annotated[Caller, Depends(require_roles("WAREHOUSE_MANAGER"))]
