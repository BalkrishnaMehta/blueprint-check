from notifications.service import notify


def charge(amount: int) -> int:
    notify(amount)
    return amount
