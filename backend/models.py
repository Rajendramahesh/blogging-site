from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Any
import uuid
from datetime import datetime


# ── Auth ────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str = ""

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3–50 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, underscores")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User ─────────────────────────────────────────────────────────────────────

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    bio: str
    avatar_url: str
    created_at: datetime
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0


class UserMe(UserPublic):
    email: str


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


# ── Author (embedded in post responses) ─────────────────────────────────────

class AuthorInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    avatar_url: str
    bio: str = ""


# ── Post ──────────────────────────────────────────────────────────────────────

class CreatePostRequest(BaseModel):
    title: str
    subtitle: str = ""
    content: dict[str, Any] = {}
    cover_image_url: str = ""
    published: bool = False

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class UpdatePostRequest(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    content: dict[str, Any] | None = None
    cover_image_url: str | None = None
    published: bool | None = None


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    subtitle: str
    content: dict[str, Any]
    cover_image_url: str
    published: bool
    reading_time_minutes: int
    created_at: datetime
    updated_at: datetime
    author: AuthorInfo
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False


class PaginatedPosts(BaseModel):
    items: list[PostResponse]
    total: int
    page: int
    limit: int
    has_next: bool


# ── Comment ──────────────────────────────────────────────────────────────────

class CreateCommentRequest(BaseModel):
    body: str

    @field_validator("body")
    @classmethod
    def body_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Comment cannot be empty")
        return v.strip()


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    body: str
    created_at: datetime
    user: AuthorInfo


class PaginatedComments(BaseModel):
    items: list[CommentResponse]
    total: int
    page: int
    limit: int
    has_next: bool


# ── Like ──────────────────────────────────────────────────────────────────────

class LikeResponse(BaseModel):
    liked: bool
    like_count: int


# ── Follow ────────────────────────────────────────────────────────────────────

class FollowResponse(BaseModel):
    following: bool


class PaginatedUsers(BaseModel):
    items: list[UserPublic]
    total: int
    page: int
    limit: int
    has_next: bool
