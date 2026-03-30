import json
import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Annotated
from db import get_pool
from models import (
    CreatePostRequest, UpdatePostRequest, PostResponse, PaginatedPosts,
)
from dependencies import get_current_user, get_optional_user
from utils import slugify, estimate_reading_time, paginate

router = APIRouter(tags=["posts"])


def _build_post(row: dict) -> dict:
    """Build a PostResponse-compatible dict from a DB row."""
    content = row.get("content", {})
    if isinstance(content, str):
        content = json.loads(content)
    return {
        **{k: v for k, v in row.items() if k not in (
            "username", "display_name", "avatar_url", "author_bio",
            "like_count", "comment_count", "liked_by_me", "content",
        )},
        "content": content,
        "author": {
            "id": row["author_id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "avatar_url": row["avatar_url"],
            "bio": row.get("author_bio", "") or "",
        },
        "like_count": int(row.get("like_count", 0) or 0),
        "comment_count": int(row.get("comment_count", 0) or 0),
        "liked_by_me": bool(row.get("liked_by_me", False)),
    }


POST_SELECT = """
    SELECT
        p.*,
        u.username, u.display_name, u.avatar_url, u.bio AS author_bio,
        COUNT(DISTINCT l.user_id)::int AS like_count,
        COUNT(DISTINCT c.id)::int AS comment_count,
        COALESCE(BOOL_OR(l.user_id = CAST(NULLIF($1, '') AS uuid)), FALSE) AS liked_by_me
    FROM posts p
    JOIN users u ON p.author_id = u.id
    LEFT JOIN likes l ON l.post_id = p.id
    LEFT JOIN comments c ON c.post_id = p.id
"""


@router.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(
    data: CreatePostRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    pool = await get_pool()
    slug = slugify(data.title)
    reading_time = estimate_reading_time(data.content)

    row = await pool.fetchrow(
        """
        INSERT INTO posts (author_id, title, slug, subtitle, content, cover_image_url, published, reading_time_minutes)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8)
        RETURNING *
        """,
        current_user["id"], data.title, slug, data.subtitle,
        json.dumps(data.content),
        data.cover_image_url, data.published, reading_time,
    )

    # Fetch full post with author info and counts
    full = await pool.fetchrow(
        POST_SELECT + " WHERE p.id=$2 GROUP BY p.id, u.id",
        str(current_user["id"]), row["id"],
    )
    return _build_post(dict(full))


@router.get("/posts", response_model=PaginatedPosts)
async def list_posts(
    current_user: Annotated[dict | None, Depends(get_optional_user)] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    author: str | None = None,
    search: str | None = None,
):
    pool = await get_pool()
    lim, offset = paginate(page, limit)
    user_id = str(current_user["id"]) if current_user else ""

    # Build dynamic WHERE conditions.
    # Parameter indices are derived from len(params) to keep placeholders in sync.
    count_conditions = ["p.published = TRUE"]
    count_params: list = []
    conditions = ["p.published = TRUE"]
    params: list = [user_id]  # $1 is always user_id for liked_by_me

    if author:
        ci = len(count_params) + 1
        count_conditions.append("u.username = $" + str(ci))
        count_params.append(author)

        pi = len(params) + 1
        conditions.append("u.username = $" + str(pi))
        params.append(author)

    if search:
        ci = len(count_params) + 1
        count_conditions.append(
            "(p.title ILIKE $" + str(ci) + " OR p.subtitle ILIKE $" + str(ci)
            + " OR u.username ILIKE $" + str(ci) + ")"
        )
        count_params.append("%" + search + "%")

        pi = len(params) + 1
        conditions.append(
            "(p.title ILIKE $" + str(pi) + " OR p.subtitle ILIKE $" + str(pi)
            + " OR u.username ILIKE $" + str(pi) + ")"
        )
        params.append("%" + search + "%")

    count_where = " AND ".join(count_conditions)
    where = " AND ".join(conditions)

    total_row = await pool.fetchrow(
        "SELECT COUNT(DISTINCT p.id)::int AS total "
        "FROM posts p JOIN users u ON p.author_id = u.id "
        "WHERE " + count_where,
        *count_params,
    )
    total = total_row["total"]

    lim_idx = len(params) + 1
    off_idx = len(params) + 2
    rows = await pool.fetch(
        POST_SELECT
        + " WHERE " + where
        + " GROUP BY p.id, u.id"
        + " ORDER BY p.created_at DESC"
        + " LIMIT $" + str(lim_idx) + " OFFSET $" + str(off_idx),
        *params, lim, offset,
    )

    items = [_build_post(dict(r)) for r in rows]
    return PaginatedPosts(
        items=items, total=total, page=page, limit=limit,
        has_next=(offset + lim < total),
    )


@router.get("/posts/{slug_or_id}", response_model=PostResponse)
async def get_post(
    slug_or_id: str,
    current_user: Annotated[dict | None, Depends(get_optional_user)] = None,
):
    pool = await get_pool()
    user_id = str(current_user["id"]) if current_user else ""

    # Try slug first (published posts)
    row = await pool.fetchrow(
        POST_SELECT + " WHERE p.slug=$2 AND p.published=TRUE GROUP BY p.id, u.id",
        user_id, slug_or_id,
    )
    if not row:
        # Try by UUID (allows author to preview draft)
        try:
            uid = uuid.UUID(slug_or_id)
            row = await pool.fetchrow(
                POST_SELECT + " WHERE p.id=$2 GROUP BY p.id, u.id",
                user_id, uid,
            )
        except ValueError:
            pass

    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return _build_post(dict(row))


@router.patch("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: uuid.UUID,
    data: UpdatePostRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    pool = await get_pool()
    existing = await pool.fetchrow("SELECT * FROM posts WHERE id=$1", post_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Post not found")
    if existing["author_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your post")

    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "content" in updates:
        updates["reading_time_minutes"] = estimate_reading_time(updates["content"])

    set_clauses = []
    values: list = [post_id]
    for i, (k, v) in enumerate(updates.items(), start=2):
        if k == "content":
            set_clauses.append(f"{k}=${i}::jsonb")
            values.append(json.dumps(v))
        else:
            set_clauses.append(f"{k}=${i}")
            values.append(v)

    set_clauses.append("updated_at=NOW()")
    await pool.execute(
        f"UPDATE posts SET {', '.join(set_clauses)} WHERE id=$1",
        *values,
    )

    row = await pool.fetchrow(
        POST_SELECT + " WHERE p.id=$2 GROUP BY p.id, u.id",
        str(current_user["id"]), post_id,
    )
    return _build_post(dict(row))


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: uuid.UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT author_id FROM posts WHERE id=$1", post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    if row["author_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your post")
    await pool.execute("DELETE FROM posts WHERE id=$1", post_id)


@router.get("/feed", response_model=PaginatedPosts)
async def get_feed(
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    pool = await get_pool()
    lim, offset = paginate(page, limit)
    user_id = str(current_user["id"])

    total_row = await pool.fetchrow(
        """
        SELECT COUNT(p.id)::int AS total
        FROM posts p
        JOIN follows f ON f.following_id = p.author_id
        WHERE f.follower_id=$1::uuid AND p.published=TRUE
        """,
        user_id,
    )
    total = total_row["total"]

    rows = await pool.fetch(
        f"""
        {POST_SELECT}
        JOIN follows f ON f.following_id = p.author_id
        WHERE f.follower_id=$1::uuid AND p.published=TRUE
        GROUP BY p.id, u.id
        ORDER BY p.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id, lim, offset,
    )

    items = [_build_post(dict(r)) for r in rows]
    return PaginatedPosts(
        items=items, total=total, page=page, limit=limit,
        has_next=(offset + lim < total),
    )


@router.get("/drafts", response_model=PaginatedPosts)
async def get_drafts(
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    pool = await get_pool()
    lim, offset = paginate(page, limit)
    user_id = str(current_user["id"])

    total_row = await pool.fetchrow(
        "SELECT COUNT(*)::int AS total FROM posts WHERE author_id=$1::uuid AND published=FALSE",
        user_id,
    )
    total = total_row["total"]

    rows = await pool.fetch(
        f"""
        {POST_SELECT}
        WHERE p.author_id=$1::uuid AND p.published=FALSE
        GROUP BY p.id, u.id
        ORDER BY p.updated_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id, lim, offset,
    )

    items = [_build_post(dict(r)) for r in rows]
    return PaginatedPosts(
        items=items, total=total, page=page, limit=limit,
        has_next=(offset + lim < total),
    )
