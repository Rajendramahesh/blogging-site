import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Annotated
from db import get_pool
from models import CreateCommentRequest, CommentResponse, PaginatedComments
from dependencies import get_current_user
from utils import paginate

router = APIRouter(tags=["comments"])


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    post_id: uuid.UUID,
    data: CreateCommentRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    pool = await get_pool()
    post = await pool.fetchrow(
        "SELECT id FROM posts WHERE id=$1 AND published=TRUE", post_id
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    row = await pool.fetchrow(
        """
        INSERT INTO comments (post_id, user_id, body) VALUES ($1, $2, $3)
        RETURNING *
        """,
        post_id, current_user["id"], data.body,
    )
    user = await pool.fetchrow(
        "SELECT id, username, display_name, avatar_url, bio FROM users WHERE id=$1",
        current_user["id"],
    )
    return {**dict(row), "user": dict(user)}


@router.get("/posts/{post_id}/comments", response_model=PaginatedComments)
async def list_comments(
    post_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    pool = await get_pool()
    lim, offset = paginate(page, limit)

    total_row = await pool.fetchrow(
        "SELECT COUNT(*)::int AS total FROM comments WHERE post_id=$1", post_id
    )
    total = total_row["total"]

    rows = await pool.fetch(
        """
        SELECT c.*, u.id AS user_id_col, u.username, u.display_name, u.avatar_url, u.bio
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.post_id=$1
        ORDER BY c.created_at ASC
        LIMIT $2 OFFSET $3
        """,
        post_id, lim, offset,
    )

    items = [
        {
            "id": r["id"],
            "body": r["body"],
            "created_at": r["created_at"],
            "user": {
                "id": r["user_id"],
                "username": r["username"],
                "display_name": r["display_name"],
                "avatar_url": r["avatar_url"],
                "bio": r["bio"],
            },
        }
        for r in rows
    ]
    return PaginatedComments(
        items=items, total=total, page=page, limit=lim,
        has_next=(offset + lim < total),
    )


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT user_id FROM comments WHERE id=$1", comment_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Comment not found")
    if row["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your comment")
    await pool.execute("DELETE FROM comments WHERE id=$1", comment_id)
