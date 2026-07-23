from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.rate_limiter import auth_limiter
from app.dependencies import AuthState, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class CurrentUserResponse(BaseModel):
    user: dict[str, Any]


@router.get("/me", response_model=CurrentUserResponse, dependencies=[Depends(auth_limiter)])
def read_current_auth(auth: AuthState = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(user={
        "id": auth.user_id,
        "email": auth.email,
        "role": auth.role,
        "metadata": auth.user_metadata,
        "profile": auth.profile,
        "profile_exists": auth.profile_exists,
    })
