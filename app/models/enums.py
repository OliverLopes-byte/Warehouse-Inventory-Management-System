from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    WAREHOUSE_MANAGER = "WAREHOUSE_MANAGER"
    STORE_CLERK = "STORE_CLERK"


class POStatus(StrEnum):   #purchase order
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
#Goods Receipt Note
#stockledger is a append only diary

class Movement(StrEnum):
    RECEIPT = "RECEIPT"
    ISSUE = "ISSUE"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT = "ADJUSTMENT"
