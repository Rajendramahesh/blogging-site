import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Annotated
from db import get_pool
from models import FollowResponse, PaginatedUsers
from dependencies import get_current_user
from utils import paginate

router = APIRouter(tags=["follows"])


@router.post("/users/{user_id}/follow", response_model=FollowResponse)
async def toggle_follow(
    user_id: uuid.UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    pool = await get_pool()
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    target = await pool.fetchrow("SELECT id FROM users WHERE id=$1", user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await pool.fetchrow(
        "SELECT 1 FROM follows WHERE follower_id=$1 AND following_id=$2",
        current_user["id"], user_id,
    )

    if existing:
        await pool.execute(
            "DELETE FROM follows WHERE follower_id=$1 AND following_id=$2",
            current_user["id"], user_id,
        )
        return FollowResponse(following=False)
    else:
        await pool.execute(
            "INSERT INTO follows (follower_id, following_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            current_user["id"], user_id,
        )
        return FollowResponse(following=True)


@router.get("/users/{username}/followers", response_model=PaginatedUsers)
async def get_followers(
    username: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    pool = await get_pool()
    lim, offset = paginate(page, limit)

    user = await pool.fetchrow("SELECT id FROM users WHERE username=$1", username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    total_row = await pool.fetchrow(
        "SELECT COUNT(*)::int AS total FROM follows WHERE following_id=$1", user["id"]
    )
    total = total_row["total"]

    rows = await pool.fetch(
        """
        SELECT u.*,
            (SELECT COUNT(*)::int FROM follows WHERE following_id=u.id) AS follower_count,
            (SELECT COUNT(*)::int FROM follows WHERE follower_id=u.id) AS following_count,
            (SELECT COUNT(*)::int FROM posts WHERE author_id=u.id AND published=TRUE) AS post_count
        FROM users u
        JOIN follows f ON f.follower_id = u.id
        WHERE f.following_id=$1
        ORDER BY f.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user["id"], lim, offset,
    )
    return PaginatedUsers(
        items=[dict(r) for r in rows],
        total=total, page=page, limit=lim,
        has_next=(offset + lim < total),
    )


@router.get("/users/{username}/following", response_model=PaginatedUsers)
async def get_following(
    username: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    pool = await get_pool()
    lim, offset = paginate(page, limit)

    user = await pool.fetchrow("SELECT id FROM users WHERE username=$1", username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    total_row = await pool.fetchrow(
        "SELECT COUNT(*)::int AS total FROM follows WHERE follower_id=$1", user["id"]
    )
    total = total_row["total"]

    rows = await pool.fetch(
        """
        SELECT u.*,
            (SELECT COUNT(*)::int FROM follows WHERE following_id=u.id) AS follower_count,
            (SELECT COUNT(*)::int FROM follows WHERE follower_id=u.id) AS following_count,
            (SELECT COUNT(*)::int FROM posts WHERE author_id=u.id AND published=TRUE) AS post_count
        FROM users u
        JOIN follows f ON f.following_id = u.id
        WHERE f.follower_id=$1
        ORDER BY f.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user["id"], lim, offset,
    )
    return PaginatedUsers(
        items=[dict(r) for r in rows],
        total=total, page=page, limit=lim,
        has_next=(offset + lim < total),
    )
