from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import Field

from app.dependencies import AuthState, RequireAdmin
from app.schemas.common import ID_RE, StrictRequestModel
from app.services.validation_service import all_cases_payload, update_case

router = APIRouter()


class ValidationUpdate(StrictRequestModel):
    expected_lagna_sign: str = Field(default="", max_length=80)
    expected_lagna_degree: str = Field(default="", max_length=80)
    expected_moon_sign: str = Field(default="", max_length=80)
    expected_moon_nakshatra: str = Field(default="", max_length=80)
    expected_moon_pada: str = Field(default="", max_length=40)
    expected_mahadasha: str = Field(default="", max_length=80)
    expected_antardasha: str = Field(default="", max_length=80)
    source_notes: str = Field(default="", max_length=2000)


@router.get("/validation/cases")
def validation_cases(auth: AuthState = Depends(RequireAdmin())) -> dict:
    return all_cases_payload()


@router.post("/validation/cases/{case_id}")
def save_validation_case(
    case_id: Annotated[str, Path(pattern=ID_RE)],
    payload: ValidationUpdate,
    auth: AuthState = Depends(RequireAdmin()),
) -> dict:
    updated = update_case(case_id, payload.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Validation case not found")
    return updated
