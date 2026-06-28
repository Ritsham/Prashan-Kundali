from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.validation_service import all_cases_payload, update_case

router = APIRouter()


class ValidationUpdate(BaseModel):
    expected_lagna_sign: str = ""
    expected_lagna_degree: str = ""
    expected_moon_sign: str = ""
    expected_moon_nakshatra: str = ""
    expected_moon_pada: str = ""
    expected_mahadasha: str = ""
    expected_antardasha: str = ""
    source_notes: str = ""


@router.get("/validation/cases")
def validation_cases() -> dict:
    return all_cases_payload()


@router.post("/validation/cases/{case_id}")
def save_validation_case(case_id: str, payload: ValidationUpdate) -> dict:
    updated = update_case(case_id, payload.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Validation case not found")
    return updated
