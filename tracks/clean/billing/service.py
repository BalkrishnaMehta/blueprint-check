from ledger.service import record


def pay(amount: int) -> int:
    return record(amount)
