from fastapi import Depends, HTTPException, status, Header
from typing import Annotated
from auth import decode_token
from db import get_pool


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_exception

    pool = await get_pool()
    row = await pool.fetchrow("""
        SELECT u.*,
               (SELECT COUNT(*)::int FROM follows WHERE following_id = u.id) AS follower_count,
               (SELECT COUNT(*)::int FROM follows WHERE follower_id = u.id) AS following_count,
               (SELECT COUNT(*)::int FROM posts WHERE author_id = u.id AND published = TRUE) AS post_count
        FROM users u WHERE u.id = $1
    """, user_id)
    if not row:
        raise credentials_exception

    return dict(row)


async def get_optional_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization=authorization)
    except HTTPException:
        return None
