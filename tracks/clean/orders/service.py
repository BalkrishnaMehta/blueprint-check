from billing.service import pay


def place(amount: int) -> int:
    return pay(amount)
