from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Difficulty = Literal["beginner", "middle school", "high school", "advanced"]
FinancialNeed = Literal["low", "medium", "high"]
AssistantMode = Literal["learning", "quiz", "help", "review"]
ScholarshipFit = Literal["High", "Medium", "Low"]

SAFETY_NOTE = "AI-generated learning support. Verify important information."
DEFAULT_QUOTE = "Understanding this topic is essential for STEM success."
SCHOLARSHIP_DISCLAIMER = "This is guidance, not a guarantee of acceptance."

ALLOWED_SOURCES = frozenset(
    {"cohere", "openrouter", "gemini", "groq", "accessstem_local", "backend"}
)


class ExplainRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    difficulty: Difficulty = "beginner"
    low_bandwidth: bool = False


class ExplainResponse(BaseModel):
    topic: str
    explanation: str
    key_concepts: list[str]
    key_points: list[str]
    example: str
    quote: str = DEFAULT_QUOTE
    next_topics: list[str]
    check_question: str
    source: str
    debug_reason: str | None = None
    provider_attempts: list[dict[str, Any]] | None = None


class QuizRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    difficulty: Difficulty = "beginner"
    question_count: int = Field(default=5, ge=3, le=7)


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str] = Field(..., min_length=4, max_length=4)
    correct: int = Field(..., ge=0, le=3)
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
    difficulty: str
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
    answer: str
    key_points: list[str]
    example: str
    next_steps: list[str]
    suggested_questions: list[str]
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
    gpa: float = Field(..., ge=0, le=4)
    country: str = Field(..., min_length=1)
    intended_major: str = Field(default="", max_length=120)
    major: str = Field(default="", max_length=120)
    first_generation: bool = False
    financial_need: bool | FinancialNeed = "medium"
    grade_level: str = Field(default="11", max_length=20)
    english_level: str = Field(default="B2", max_length=20)
    activities: str = ""
    has_essay: bool = False
    has_english_test: bool = False

    @model_validator(mode="after")
    def normalize_profile(self) -> "ScholarshipRequest":
        if not self.intended_major.strip() and self.major.strip():
            self.intended_major = self.major.strip()
        if not self.intended_major.strip():
            self.intended_major = "STEM"
        return self

    @property
    def financial_need_level(self) -> FinancialNeed:
        if isinstance(self.financial_need, bool):
            return "high" if self.financial_need else "low"
        return self.financial_need


class RecommendedScholarship(BaseModel):
    name: str
    fit: ScholarshipFit
    reason: str


class ScholarshipResponse(BaseModel):
    fit_score: int = Field(..., ge=0, le=100)
    readiness_score: int = Field(..., ge=0, le=100)
    summary: str
    strengths: list[str]
    improvements: list[str]
    recommended_scholarships: list[RecommendedScholarship]
    required_documents: list[str]
    next_steps: list[str]
    disclaimer: str = SCHOLARSHIP_DISCLAIMER
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
    student_id: str
    topic: str
    score: int
    total: int
    percentage: int


class RecentScore(BaseModel):
    topic: str
    score: int
    total: int
    percentage: int


class DashboardResponse(BaseModel):
    student_id: str
    topics_completed: int
    quizzes_taken: int
    average_score: int
    last_topic: str
    recent_scores: list[RecentScore]
    recommended_next_topic: str
    source: str = "backend"


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
    database_configured: bool
    version: str


class AiStatusResponse(BaseModel):
    cohere_enabled: bool
    cohere_configured: bool
    openrouter_enabled: bool
    openrouter_configured: bool
    gemini_enabled: bool
    gemini_configured: bool
    groq_enabled: bool
    groq_configured: bool
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
