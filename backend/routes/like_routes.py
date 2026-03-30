import uuid
from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from db import get_pool
from models import LikeResponse
from dependencies import get_current_user

router = APIRouter(tags=["likes"])


@router.post("/posts/{post_id}/like", response_model=LikeResponse)
async def toggle_like(
    post_id: uuid.UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    pool = await get_pool()
    post = await pool.fetchrow(
        "SELECT id FROM posts WHERE id=$1 AND published=TRUE", post_id
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = await pool.fetchrow(
        "SELECT 1 FROM likes WHERE user_id=$1 AND post_id=$2",
        current_user["id"], post_id,
    )

    if existing:
        await pool.execute(
            "DELETE FROM likes WHERE user_id=$1 AND post_id=$2",
            current_user["id"], post_id,
        )
        liked = False
    else:
        await pool.execute(
            "INSERT INTO likes (user_id, post_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            current_user["id"], post_id,
        )
        liked = True

    count_row = await pool.fetchrow(
        "SELECT COUNT(*)::int AS c FROM likes WHERE post_id=$1", post_id
    )
    return LikeResponse(liked=liked, like_count=count_row["c"])


@router.get("/posts/{post_id}/likes")
async def get_likes(post_id: uuid.UUID):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT COUNT(*)::int AS like_count FROM likes WHERE post_id=$1", post_id
    )
    return {"post_id": str(post_id), "like_count": row["like_count"]}
