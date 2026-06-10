import re

from fastapi import APIRouter

from app.ai_engine import (
    generate_assistant,
    generate_explanation,
    generate_hint,
    generate_quiz,
    generate_recommend_next,
    generate_review_quiz,
    generate_study_plan,
)
from app.safety import check_payload_safety, validate_text_field, validate_topic
from app.schemas import (
    AssistantRequest,
    AssistantResponse,
    CheckAnswerRequest,
    CheckAnswerResponse,
    ExplainRequest,
    ExplainResponse,
    HintRequest,
    HintResponse,
    QuizRequest,
    QuizResponse,
    RecommendNextRequest,
    RecommendNextResponse,
    ReviewQuizRequest,
    ReviewQuizResponse,
    StudyPlanRequest,
    StudyPlanResponse,
)
from app.storage import get_storage

router = APIRouter(prefix="/api/accessstem", tags=["AccessSTEM AI"])


def _normalize_answer(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _compare_answers(student_answer: str, correct_answer: str) -> bool:
    student = _normalize_answer(student_answer)
    correct = _normalize_answer(correct_answer)
    if not student or not correct:
        return False
    if student == correct:
        return True
    if len(correct) > 12 and (student in correct or correct in student):
        return True
    return False


def _log_ai_request(endpoint: str, topic: str | None, result: dict) -> None:
    source = str(result.get("source", "unknown"))
    is_ai_provider = source in {"cohere", "openrouter", "gemini", "groq"}
    get_storage().log_ai_request(
        endpoint=endpoint,
        topic=topic,
        source=source,
        success=True,
        error_code=None if is_ai_provider else "LOCAL_ENGINE",
    )


@router.post("/assistant", response_model=AssistantResponse, response_model_exclude_none=True)
def assistant(request: AssistantRequest) -> dict:
    topic = validate_topic(request.topic)
    question = validate_text_field(request.question, "question")
    student_context = (
        validate_text_field(request.student_context, "student_context")
        if request.student_context.strip()
        else ""
    )
    check_payload_safety(
        {
            "topic": topic,
            "question": question,
            "student_context": student_context,
        }
    )
    result = generate_assistant(
        topic,
        question,
        request.difficulty,
        request.mode,
        student_context,
    )
    _log_ai_request("/api/accessstem/assistant", topic, result)
    return result


@router.post("/explain", response_model=ExplainResponse, response_model_exclude_none=True)
def explain(request: ExplainRequest) -> dict:
    topic = validate_topic(request.topic)
    check_payload_safety(request.model_dump())
    result = generate_explanation(topic, request.difficulty, request.low_bandwidth)
    _log_ai_request("/api/accessstem/explain", topic, result)
    return result


@router.post("/quiz", response_model=QuizResponse, response_model_exclude_none=True)
def quiz(request: QuizRequest) -> dict:
    topic = validate_topic(request.topic)
    check_payload_safety(request.model_dump())
    result = generate_quiz(topic, request.difficulty, request.question_count)
    _log_ai_request("/api/accessstem/quiz", topic, result)
    return result


@router.post("/hint", response_model=HintResponse, response_model_exclude_none=True)
def hint(request: HintRequest) -> dict:
    topic = validate_topic(request.topic)
    question = validate_text_field(request.question, "question")
    student_answer = validate_text_field(request.student_answer, "student_answer")
    correct_answer = validate_text_field(request.correct_answer, "correct_answer")
    check_payload_safety(request.model_dump())
    result = generate_hint(topic, question, student_answer, correct_answer)
    _log_ai_request("/api/accessstem/hint", topic, result)
    return result


@router.post("/check-answer", response_model=CheckAnswerResponse)
def check_answer(request: CheckAnswerRequest) -> dict:
    question = validate_text_field(request.question, "question")
    student_answer = validate_text_field(request.student_answer, "student_answer")
    correct_answer = validate_text_field(request.correct_answer, "correct_answer")
    check_payload_safety(
        {
            "question": question,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "explanation": request.explanation,
        }
    )

    is_correct = _compare_answers(student_answer, correct_answer)
    if is_correct:
        feedback = "Correct! Nice work — you understood the concept."
        score_delta = 1
    else:
        feedback = (
            request.explanation.strip()
            or "Not quite. Review the concept, use a hint, and try again."
        )
        score_delta = 0

    return {
        "is_correct": is_correct,
        "feedback": feedback,
        "score_delta": score_delta,
    }


@router.post("/review-quiz", response_model=ReviewQuizResponse, response_model_exclude_none=True)
def review_quiz(request: ReviewQuizRequest) -> dict:
    topic = validate_topic(request.topic)
    weak_concepts = [validate_topic(c) for c in request.weak_concepts if c.strip()]
    check_payload_safety({"topic": topic, "weak_concepts": weak_concepts})
    result = generate_review_quiz(
        topic,
        request.difficulty,
        request.score,
        request.total,
        weak_concepts,
    )
    _log_ai_request("/api/accessstem/review-quiz", topic, result)
    return result


@router.post("/recommend-next", response_model=RecommendNextResponse, response_model_exclude_none=True)
def recommend_next(request: RecommendNextRequest) -> dict:
    topic = validate_topic(request.topic)
    completed = [validate_topic(t) for t in request.completed_topics if t.strip()]
    check_payload_safety({"topic": topic, "completed_topics": completed})
    result = generate_recommend_next(
        topic,
        request.difficulty,
        completed,
        request.score,
        request.total,
    )
    _log_ai_request("/api/accessstem/recommend-next", topic, result)
    return result


@router.post("/study-plan", response_model=StudyPlanResponse, response_model_exclude_none=True)
def study_plan(request: StudyPlanRequest) -> dict:
    goal = validate_text_field(request.goal, "goal")
    grade_level = validate_text_field(request.grade_level, "grade_level")
    weak_topics = [validate_topic(topic) for topic in request.weak_topics if topic.strip()]
    check_payload_safety({"goal": goal, "grade_level": grade_level, "weak_topics": weak_topics})
    result = generate_study_plan(goal, grade_level, request.available_days, weak_topics)
    _log_ai_request("/api/accessstem/study-plan", goal, result)
    return result
