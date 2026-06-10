from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Difficulty = Literal["beginner", "middle school", "high school", "advanced"]
FinancialNeed = Literal["low", "medium", "high"]
AssistantMode = Literal["learning", "quiz", "help", "review"]

SAFETY_NOTE = "AI-generated learning support. Verify important information."


class ExplainRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    difficulty: Difficulty = "beginner"
    low_bandwidth: bool = False


class ExplainResponse(BaseModel):
    topic: str
    level: str
    explanation: str
    example: str
    key_points: list[str]
    check_question: str
    next_topics: list[str]
    safety_note: str = SAFETY_NOTE
    source: str
    debug_reason: str | None = None
    provider_attempts: list[dict[str, Any]] | None = None


class QuizRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    difficulty: Difficulty = "beginner"
    question_count: int = Field(default=5, ge=3, le=7)


class QuizQuestion(BaseModel):
    id: str
    question: str
    options: list[str] = Field(..., min_length=4, max_length=4)
    correct_answer: str
    explanation: str
    concept: str

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[str]) -> list[str]:
        cleaned = [option.strip() for option in value if option and option.strip()]
        if len(cleaned) != 4:
            raise ValueError("Each question must have exactly 4 options")
        return cleaned


class QuizResponse(BaseModel):
    topic: str
    level: str
    questions: list[QuizQuestion]
    source: str
    debug_reason: str | None = None
    provider_attempts: list[dict[str, Any]] | None = None


class HintRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    student_answer: str = Field(..., min_length=1)
    correct_answer: str = Field(..., min_length=1)


class HintResponse(BaseModel):
    hint: str
    encouragement: str
    reveals_answer: bool = False
    source: str
    debug_reason: str | None = None
    provider_attempts: list[dict[str, Any]] | None = None


class CheckAnswerRequest(BaseModel):
    question: str = Field(..., min_length=1)
    student_answer: str = Field(..., min_length=1)
    correct_answer: str = Field(..., min_length=1)
    explanation: str = ""


class CheckAnswerResponse(BaseModel):
    is_correct: bool
    feedback: str
    score_delta: int


class AssistantRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    difficulty: Difficulty = "beginner"
    mode: AssistantMode = "learning"
    student_context: str = ""


class AssistantResponse(BaseModel):
    topic: str
    answer: str
    key_points: list[str]
    example: str
    next_steps: list[str]
    suggested_questions: list[str]
    safety_note: str = SAFETY_NOTE
    source: str
    debug_reason: str | None = None
    provider_attempts: list[dict[str, Any]] | None = None


class StudyPlanRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    grade_level: str = Field(..., min_length=1)
    available_days: int = Field(..., ge=1, le=14)
    weak_topics: list[str] = Field(default_factory=list)


class StudyPlanDay(BaseModel):
    day: int
    focus: str
    tasks: list[str]
    estimated_minutes: int


class StudyPlanResponse(BaseModel):
    goal: str
    days: list[StudyPlanDay]
    source: str
    debug_reason: str | None = None
    provider_attempts: list[dict[str, Any]] | None = None


class ScholarshipRequest(BaseModel):
    grade_level: str = Field(..., min_length=1)
    gpa: float = Field(..., ge=0, le=4)
    country: str = Field(..., min_length=1)
    intended_major: str = Field(..., min_length=1)
    english_level: str = Field(..., min_length=1)
    financial_need: FinancialNeed = "medium"
    activities: str = ""
    has_essay: bool = False
    has_english_test: bool = False


class ScholarshipMatch(BaseModel):
    name: str
    category: str
    fit_score: int = Field(..., ge=0, le=100)
    estimated_amount: int
    deadline: str
    strengths: list[str]
    improvements: list[str]
    required_documents: list[str]


class ScholarshipAdvisor(BaseModel):
    summary: str
    next_steps: list[str]
    warning: str = "This is an estimate and does not guarantee acceptance."


class ScholarshipResponse(BaseModel):
    profile_summary: str
    overall_readiness_score: int = Field(..., ge=0, le=100)
    matches: list[ScholarshipMatch]
    advisor: ScholarshipAdvisor
    source: str
    debug_reason: str | None = None
    provider_attempts: list[dict[str, Any]] | None = None


class ProgressCreateRequest(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=120)
    topic: str = Field(..., min_length=1)
    score: int = Field(..., ge=0)
    total: int = Field(..., ge=1, le=100)


class ProgressItem(BaseModel):
    id: str
    student_id: str
    topic: str
    score: int
    total: int
    percentage: int
    created_at: str


class ProgressSaveResponse(BaseModel):
    saved: bool
    item: ProgressItem


class ProgressListResponse(BaseModel):
    student_id: str
    items: list[ProgressItem]
    average_percentage: int
    completed_topics: int


class ReviewQuizRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    difficulty: Difficulty = "beginner"
    score: int = Field(..., ge=0)
    total: int = Field(..., ge=1, le=100)
    weak_concepts: list[str] = Field(default_factory=list)


class ReviewQuizResponse(BaseModel):
    topic: str
    summary: str
    strengths: list[str]
    improvements: list[str]
    next_steps: list[str]
    source: str
    debug_reason: str | None = None
    provider_attempts: list[dict[str, Any]] | None = None


class RecommendNextRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    difficulty: Difficulty = "beginner"
    completed_topics: list[str] = Field(default_factory=list)
    score: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=1, le=100)


class RecommendNextResponse(BaseModel):
    current_topic: str
    recommended_topics: list[str]
    reason: str
    study_tip: str
    source: str
    debug_reason: str | None = None
    provider_attempts: list[dict[str, Any]] | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    ai_configured: bool
    cohere_configured: bool
    openrouter_configured: bool
    gemini_configured: bool
    groq_configured: bool
    database_configured: bool
    version: str


class AiStatusResponse(BaseModel):
    cohere_enabled: bool
    cohere_configured: bool
    cohere_model: str
    openrouter_configured: bool
    openrouter_enabled: bool
    gemini_enabled: bool
    groq_enabled: bool
    active_strategy: str


class ProviderDiagnostic(BaseModel):
    enabled: bool
    configured: bool
    ok: bool
    error_code: str | None = None


class ProviderTestResponse(BaseModel):
    cohere: ProviderDiagnostic
    openrouter: ProviderDiagnostic
    gemini: ProviderDiagnostic
    groq: ProviderDiagnostic


class MetaResponse(BaseModel):
    name: str
    core_engine: str
    version: str
    features: list[str]
