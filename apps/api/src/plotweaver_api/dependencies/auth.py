from fastapi import Header


def get_user_id(x_user_id: str | None = Header(default=None)) -> str | None:
    return x_user_id
