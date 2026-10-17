from warehouse.service import reserve


def start(order: int) -> int:
    return reserve(order)
