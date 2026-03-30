from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from db import get_pool
from models import UserPublic, UpdateProfileRequest
from dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{username}", response_model=UserPublic)
async def get_user_profile(username: str):
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT
            u.*,
            COUNT(DISTINCT f1.follower_id)::int AS follower_count,
            COUNT(DISTINCT f2.following_id)::int AS following_count,
            COUNT(DISTINCT p.id)::int AS post_count
        FROM users u
        LEFT JOIN follows f1 ON f1.following_id = u.id
        LEFT JOIN follows f2 ON f2.follower_id = u.id
        LEFT JOIN posts p ON p.author_id = u.id AND p.published = TRUE
        WHERE u.username = $1
        GROUP BY u.id
        """,
        username,
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


@router.patch("/me", response_model=UserPublic)
async def update_profile(
    data: UpdateProfileRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    pool = await get_pool()
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    fields = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates.keys()))
    values = list(updates.values())

    row = await pool.fetchrow(
        f"""
        UPDATE users
        SET {fields}, updated_at=NOW()
        WHERE id=$1
        RETURNING *,
            (SELECT COUNT(*)::int FROM follows WHERE following_id=id) AS follower_count,
            (SELECT COUNT(*)::int FROM follows WHERE follower_id=id) AS following_count,
            (SELECT COUNT(*)::int FROM posts WHERE author_id=id AND published=TRUE) AS post_count
        """,
        current_user["id"], *values,
    )
    return dict(row)
