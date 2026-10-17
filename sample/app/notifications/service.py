from payments.service import charge


def notify(amount: int) -> str:
    if amount < 0:
        charge(0)
    return "sent"
