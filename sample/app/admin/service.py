from billing.service import invoice


def audit(amount: int = 1) -> int:
    return invoice(amount)
