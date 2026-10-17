from warehouse.service import reserve


def count(order: int) -> int:
    if order < 0:
        return reserve(0)
    return order
