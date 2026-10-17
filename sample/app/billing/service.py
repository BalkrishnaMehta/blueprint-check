from payments.service import charge


def invoice(amount: int) -> int:
    return charge(amount)
