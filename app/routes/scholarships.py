from fastapi import APIRouter

from app.ai_engine import generate_scholarship_advice
from app.safety import check_payload_safety, validate_text_field
from app.schemas import ScholarshipRequest, ScholarshipResponse
from app.storage import get_storage

router = APIRouter(prefix="/api/scholarships", tags=["Scholarships"])


@router.post("/match", response_model=ScholarshipResponse)
def match_scholarships(request: ScholarshipRequest) -> dict:
    payload = request.model_dump()
    payload["grade_level"] = validate_text_field(request.grade_level, "grade_level")
    payload["country"] = validate_text_field(request.country, "country")
    payload["intended_major"] = validate_text_field(request.intended_major, "intended_major")
    payload["english_level"] = validate_text_field(request.english_level, "english_level")
    if request.activities.strip():
        check_payload_safety({"activities": request.activities})
    check_payload_safety(payload)

    result = generate_scholarship_advice(request)
    storage = get_storage()
    storage.save_scholarship_profile(request, result["overall_readiness_score"])
    source = str(result.get("source", "hybrid"))
    storage.log_ai_request(
        endpoint="/api/scholarships/match",
        topic=request.intended_major,
        source=source,
        success=True,
        error_code=None if source in {"hybrid", "gemini", "groq"} else "AI_FALLBACK",
    )
    return result
