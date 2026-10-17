from admin.service import audit


def login(user: str) -> str:
    audit()
    return user
