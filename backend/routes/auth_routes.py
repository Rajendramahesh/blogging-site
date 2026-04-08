from fastapi import APIRouter, HTTPException, status, Response, Cookie, Depends
from typing import Annotated
from db import get_pool
from auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from models import SignupRequest, LoginRequest, TokenResponse, UserMe
from config import settings
from dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
COOKIE_MAX_AGE = settings.refresh_token_expire_days * 24 * 3600


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest, response: Response):
    pool = await get_pool()
    existing = await pool.fetchrow(
        "SELECT id FROM users WHERE email=$1 OR username=$2",
        data.email, data.username,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email or username already in use")

    pw_hash = hash_password(data.password)
    row = await pool.fetchrow(
        """
        INSERT INTO users (username, email, password_hash, display_name)
        VALUES ($1, $2, $3, $4) RETURNING id
        """,
        data.username, data.email, pw_hash, data.display_name or data.username,
    )
    user_id = str(row["id"])
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE email=$1", data.email)
    if not row or not verify_password(data.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(row["id"])
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    pool = await get_pool()
    row = await pool.fetchrow("SELECT id FROM users WHERE id=$1", user_id)
    if not row:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=new_access)


@router.get("/me", response_model=UserMe)
async def get_me(current_user: Annotated[dict, Depends(get_current_user)]):
    return current_user
