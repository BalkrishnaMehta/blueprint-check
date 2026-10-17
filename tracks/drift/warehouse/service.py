from inventory.service import count


def reserve(order: int) -> int:
    return count(order)
