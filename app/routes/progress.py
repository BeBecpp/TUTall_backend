from fastapi import APIRouter, Query

from app.safety import validate_text_field, validate_topic
from app.schemas import ProgressCreateRequest, ProgressListResponse, ProgressSaveResponse
from app.storage import get_storage

router = APIRouter(prefix="/api/progress", tags=["Progress"])


@router.post("", response_model=ProgressSaveResponse)
def save_progress(request: ProgressCreateRequest) -> dict:
    student_id = validate_text_field(request.student_id, "student_id")
    topic = validate_topic(request.topic)
    storage = get_storage()
    result = storage.save_progress(student_id, topic, request.score, request.total)
    return result.model_dump()


@router.get("", response_model=ProgressListResponse)
def list_progress(student_id: str = Query(..., min_length=1)) -> dict:
    student_id = validate_text_field(student_id, "student_id")
    storage = get_storage()
    return storage.list_progress(student_id).model_dump()


@router.delete("")
def delete_progress(student_id: str = Query(..., min_length=1)) -> dict:
    student_id = validate_text_field(student_id, "student_id")
    storage = get_storage()
    return storage.clear_progress(student_id)
