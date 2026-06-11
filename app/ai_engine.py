import json
import logging
import re
from typing import Any

from app.config import get_settings
from app.fallback import (
    fallback_assistant,
    fallback_explanation,
    fallback_hint,
    fallback_quiz,
    fallback_recommend_next,
    fallback_review_quiz,
    fallback_scholarship_match,
    fallback_study_plan,
)
from app.providers import generate_with_providers, generate_text_with_providers
from app.schemas import (
    DEFAULT_QUOTE,
    AssistantResponse,
    ExplainResponse,
    QuizQuestion,
    QuizResponse,
    RecommendNextResponse,
    ReviewQuizResponse,
    SAFETY_NOTE,
    SCHOLARSHIP_DISCLAIMER,
    ScholarshipRequest,
    ScholarshipResponse,
    StudyPlanDay,
    StudyPlanResponse,
)
from app.topic_knowledge import build_topic_quiz_questions

logger = logging.getLogger(__name__)

GENERIC_EXPLANATION_MARKERS = (
    "can be learned step by step",
    "learn the main idea",
    "understand the main idea in simple words",
    "first, understand the main idea",
    "practice with hints instead of copying",
)

SYSTEM_IDENTITY = (
    "You are AccessSTEM AI, a friendly and accurate STEM tutor for TUTall. "
    "Teach with simple English. Be specific to the requested topic. "
    "Support learning, not cheating. Do not invent advanced facts. "
    "If asked for homework answers only, guide with explanation and hints."
)


def _repair_json_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"```(?:json)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()
    cleaned = re.sub(r",\s*}", "}", cleaned)
    cleaned = re.sub(r",\s*]", "]", cleaned)
    return cleaned


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = _repair_json_text(text)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", cleaned, 0)

    depth = 0
    for index, char in enumerate(cleaned[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                parsed = json.loads(cleaned[start : index + 1])
                if isinstance(parsed, dict):
                    return parsed
                break

    raise json.JSONDecodeError("No valid JSON object found", cleaned, 0)


def _extract_quiz_questions_from_text(text: str) -> list[dict[str, Any]]:
    """Recover quiz questions from malformed or partial provider JSON."""
    cleaned = _repair_json_text(text)

    try:
        data = _extract_json(cleaned)
        raw = data.get("questions", [])
        if isinstance(raw, list) and raw:
            return raw
    except json.JSONDecodeError:
        pass

    match = re.search(r'"questions"\s*:\s*(\[[\s\S]*?\])\s*[,}]', cleaned)
    if match:
        try:
            parsed = json.loads(_repair_json_text(match.group(1)))
            if isinstance(parsed, list) and parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    object_matches = re.findall(r"\{[^{}]*\"question\"\s*:\s*\"[^\"]+\"[^{}]*\}", cleaned)
    recovered: list[dict[str, Any]] = []
    for chunk in object_matches:
        try:
            item = json.loads(_repair_json_text(chunk))
            if isinstance(item, dict) and item.get("question"):
                recovered.append(item)
        except json.JSONDecodeError:
            continue

    return recovered


def _truncate_words(text: str, max_words: int = 60) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _resolve_correct_answer(correct: str, options: list[str]) -> str | None:
    normalized = correct.strip()
    if normalized in options:
        return normalized

    lowered = normalized.lower()
    for option in options:
        if option.lower() == lowered:
            return option

    for option in options:
        option_lower = option.lower()
        if lowered in option_lower or option_lower in lowered:
            return option

    letter_match = re.match(r"^[A-Da-d][\).:\s-]+(.+)$", normalized)
    if letter_match:
        letter_text = letter_match.group(1).strip().lower()
        for option in options:
            if option.lower() == letter_text:
                return option

    return None


def _is_generic_explanation(topic: str, explanation: str) -> bool:
    lowered = explanation.lower()
    topic_token = topic.lower().strip()
    if topic_token and topic_token in lowered:
        return False
    return any(marker in lowered for marker in GENERIC_EXPLANATION_MARKERS)


def _ensure_no_guarantee(summary: str) -> str:
    lowered = summary.lower()
    risky_terms = (
        "guaranteed acceptance",
        "guaranteed scholarship",
        "certain to receive",
        "will definitely win",
        "assured acceptance",
        "100% chance",
    )
    if any(term in lowered for term in risky_terms):
        return (
            "These are estimated readiness insights only. "
            "TUTall does not guarantee scholarship acceptance."
        )
    if "guarantee" in lowered and "does not guarantee" not in lowered:
        return (
            f"{summary.rstrip('.')}. "
            "This is an estimate and does not guarantee acceptance."
        )
    return summary


def _normalize_quiz_options(raw_options: Any, topic: str, index: int) -> list[str]:
    options = [str(opt).strip() for opt in (raw_options or []) if str(opt).strip()]
    while len(options) < 4:
        options.append(f"Option {len(options) + 1} for {topic}")
    return options[:4]


def _correct_index(options: list[str], correct_answer: str) -> int:
    try:
        return options.index(correct_answer)
    except ValueError:
        return 0


def _dict_to_quiz_question(raw: dict[str, Any], index: int, topic: str) -> QuizQuestion:
    options = _normalize_quiz_options(raw.get("options"), topic, index)
    correct_answer = _resolve_correct_answer(str(raw.get("correct_answer", "")).strip(), options) or options[0]
    if "correct" in raw and isinstance(raw["correct"], int) and 0 <= raw["correct"] < len(options):
        correct_idx = raw["correct"]
        correct_answer = options[correct_idx]
    else:
        correct_idx = _correct_index(options, correct_answer)
    return QuizQuestion(
        id=index,
        question=str(raw.get("question", "")).strip() or f"What is an important idea about {topic}?",
        options=options,
        correct=correct_idx,
        correct_answer=correct_answer,
        explanation=str(raw.get("explanation", "")).strip() or "Review the concept and try again.",
        concept=str(raw.get("concept", "")).strip() or topic,
    )


def _parse_quiz_questions(
    raw_questions: list[dict[str, Any]],
    topic: str,
    *,
    lenient: bool = False,
) -> list[QuizQuestion]:
    questions: list[QuizQuestion] = []
    for index, raw in enumerate(raw_questions, start=1):
        if not isinstance(raw, dict):
            if lenient:
                continue
            raise ValueError("Invalid quiz question object")

        if not lenient and len([opt for opt in raw.get("options", []) if str(opt).strip()]) != 4:
            raise ValueError("Invalid quiz options count")

        question_text = str(raw.get("question", "")).strip()
        if not question_text:
            if lenient:
                continue
            raise ValueError("Quiz question text is empty")

        try:
            questions.append(_dict_to_quiz_question(raw, index, topic))
        except ValueError:
            if lenient:
                continue
            raise
    return questions


def _repair_quiz_count(
    questions: list[QuizQuestion],
    topic: str,
    question_count: int,
) -> list[QuizQuestion]:
    if len(questions) > question_count:
        return questions[:question_count]

    if len(questions) < question_count:
        fillers = build_topic_quiz_questions(
            topic,
            question_count - len(questions),
            start_id=len(questions) + 1,
        )
        for filler in fillers:
            questions.append(QuizQuestion(**filler))

    renumbered: list[QuizQuestion] = []
    for index, question in enumerate(questions[:question_count], start=1):
        renumbered.append(question.model_copy(update={"id": index}))

    return renumbered


def _build_quiz_response(
    data: dict[str, Any],
    topic: str,
    difficulty: str,
    question_count: int,
    source: str,
    *,
    lenient: bool = False,
) -> dict:
    raw_questions = data.get("questions", [])
    if not isinstance(raw_questions, list) or not raw_questions:
        raise ValueError("No quiz questions found")

    parsed = _parse_quiz_questions(raw_questions, topic, lenient=lenient)
    if not parsed:
        raise ValueError("No usable quiz questions")

    repaired = _repair_quiz_count(parsed, topic, question_count)
    if len(repaired) != question_count:
        raise ValueError("Quiz repair failed")

    return QuizResponse(
        topic=data.get("topic") or topic,
        difficulty=data.get("difficulty") or data.get("level") or difficulty,
        questions=repaired,
        source=source,
    ).model_dump()


def _parse_quiz_from_provider_text(text: str, topic: str, difficulty: str, question_count: int, source: str) -> dict:
    recovered = _extract_quiz_questions_from_text(text)
    if recovered:
        return _build_quiz_response(
            {"topic": topic, "difficulty": difficulty, "questions": recovered},
            topic,
            difficulty,
            question_count,
            source,
            lenient=True,
        )

    try:
        data = _extract_json(text)
        return _build_quiz_response(data, topic, difficulty, question_count, source, lenient=True)
    except json.JSONDecodeError as exc:
        raise ValueError("No usable quiz content") from exc


def _normalize_study_plan_days(
    raw_days: list[dict[str, Any]],
    available_days: int,
    goal: str,
    grade_level: str,
    weak_topics: list[str],
) -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_days[:available_days], start=1):
        tasks = [str(task).strip() for task in raw.get("tasks", []) if str(task).strip()]
        if len(tasks) < 2:
            tasks = [
                f"Review key ideas for day {index}",
                "Complete 3 practice questions",
            ]
        days.append(
            StudyPlanDay(
                day=index,
                focus=str(raw.get("focus") or f"Day {index}: {goal}").strip(),
                tasks=tasks[:4],
                estimated_minutes=int(raw.get("estimated_minutes") or 45),
            ).model_dump()
        )

    while len(days) < available_days:
        filler = fallback_study_plan(goal, grade_level, available_days, weak_topics)
        days.append(filler["days"][len(days)])

    return days[:available_days]


def _hint_reveals_answer(hint: str, correct_answer: str) -> bool:
    hint_lower = hint.lower()
    answer_lower = correct_answer.lower().strip()
    if not answer_lower:
        return False
    if answer_lower in hint_lower:
        return True
    words = [word for word in answer_lower.split() if len(word) > 4]
    if words and sum(1 for word in words if word in hint_lower) >= max(2, len(words) // 2):
        return True
    return False


def _assistant_from_text(
    text: str,
    topic: str,
    question: str,
    source: str,
) -> dict:
    try:
        data = _extract_json(text)
        answer = str(data.get("answer", "")).strip()
        if answer and not _is_generic_explanation(topic, answer):
            data["key_points"] = (data.get("key_points") or [])[:4]
            data["next_steps"] = (data.get("next_steps") or [])[:4]
            data["suggested_questions"] = (data.get("suggested_questions") or [])[:4]
            if len(data["key_points"]) < 3:
                raise ValueError("Insufficient key points")
            return AssistantResponse(
                answer=answer,
                key_points=data["key_points"],
                example=str(data.get("example", "")).strip() or f"A real-world example helps with {topic}.",
                next_steps=data["next_steps"],
                suggested_questions=data["suggested_questions"],
                source=source,
            ).model_dump()
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    plain = text.strip()
    if not plain:
        raise ValueError("Empty assistant text")

    return AssistantResponse(
        answer=plain,
        key_points=[
            f"Focus on the core idea of {topic}",
            "Connect the concept to a real example",
            "Practice explaining it in your own words",
        ],
        example=f"A real-world example can help you understand {topic} better.",
        next_steps=[
            f"Review the main ideas of {topic}",
            "Try a short practice question",
        ],
        suggested_questions=[
            f"Can you give another example of {topic}?",
            f"What should I study next after {topic}?",
            question,
        ],
        source=source,
    ).model_dump()


def _shape_explain_response(data: dict[str, Any], topic: str, source: str) -> dict:
    key_points = [str(point).strip() for point in (data.get("key_points") or []) if str(point).strip()]
    key_concepts = [str(point).strip() for point in (data.get("key_concepts") or key_points) if str(point).strip()]
    if len(key_points) < 3:
        raise ValueError("Insufficient key points")
    return ExplainResponse(
        topic=data.get("topic") or topic,
        explanation=str(data.get("explanation", "")).strip(),
        key_concepts=key_concepts[:3],
        key_points=key_points[:3],
        example=str(data.get("example", "")).strip(),
        quote=str(data.get("quote", "")).strip() or DEFAULT_QUOTE,
        next_topics=(data.get("next_topics") or [])[:2],
        check_question=str(data.get("check_question", "")).strip(),
        source=source,
    ).model_dump()


def generate_explanation(topic: str, difficulty: str, low_bandwidth: bool) -> dict:
    word_limit = 120 if low_bandwidth else 180
    prompt = f"""
Return ONLY valid JSON. No markdown.

{SYSTEM_IDENTITY}

Explain this specific STEM topic for a student.
Topic: {topic}
Difficulty: {difficulty}
Low bandwidth: {low_bandwidth}

Requirements:
- The explanation MUST be about "{topic}" specifically — not generic study advice
- Mention "{topic}" or its core concepts by name
- Use simple English under {word_limit} words
- Include exactly 3 key_points about {topic}
- Include exactly 2 next_topics related to {topic}
- Include one check_question about {topic}
- Include one real-world example of {topic}
- Do not hallucinate formulas or facts you are unsure about

JSON:
{{
  "topic": "{topic}",
  "explanation": "topic-specific explanation",
  "example": "real-world example",
  "key_concepts": ["point about {topic}", "point 2", "point 3"],
  "key_points": ["point about {topic}", "point 2", "point 3"],
  "quote": "{DEFAULT_QUOTE}",
  "check_question": "question about {topic}",
  "next_topics": ["related topic 1", "related topic 2"]
}}
"""

    def parse_explanation(text: str, source: str) -> dict:
        data = _extract_json(text)
        explanation = str(data.get("explanation", "")).strip()
        if not explanation or _is_generic_explanation(topic, explanation):
            raise ValueError("Generic or empty explanation")
        return _shape_explain_response(data, topic, source)

    return generate_with_providers(
        prompt,
        parse_explanation,
        lambda: fallback_explanation(topic, difficulty, low_bandwidth),
    )


def generate_quiz(topic: str, difficulty: str, question_count: int) -> dict:
    prompt = f"""
Return ONLY valid JSON. No markdown.

{SYSTEM_IDENTITY}

Create a multiple-choice quiz about: {topic}
Difficulty: {difficulty}
Question count: EXACTLY {question_count}

Requirements:
- Every question must test knowledge of {topic} specifically
- No generic study-habit questions
- Exactly {question_count} questions in the questions array
- Each question: exactly 4 options
- correct_answer must exactly match one option text
- Include id, explanation, and concept for each question

JSON:
{{
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "questions": [
    {{
      "id": 1,
      "question": "question about {topic}",
      "options": ["A", "B", "C", "D"],
      "correct": 0,
      "correct_answer": "A",
      "explanation": "short explanation",
      "concept": "concept label"
    }}
  ]
}}
"""

    def parse_quiz(text: str, source: str) -> dict:
        return _parse_quiz_from_provider_text(text, topic, difficulty, question_count, source)

    return generate_with_providers(
        prompt,
        parse_quiz,
        lambda: fallback_quiz(topic, difficulty, question_count),
    )


def generate_hint(
    topic: str,
    question: str,
    student_answer: str,
    correct_answer: str,
) -> dict:
    prompt = f"""
{SYSTEM_IDENTITY}

Give ONE helpful hint for this quiz question.
Do NOT reveal the final answer directly.
Keep the hint under 60 words.
Be specific to the topic: {topic}

Question: {question}
Student answer: {student_answer}
Correct answer: {correct_answer}
"""

    def parse_hint(text: str, source: str) -> dict:
        hint = _truncate_words(text, max_words=60)
        if not hint or _hint_reveals_answer(hint, correct_answer):
            raise ValueError("Hint reveals answer or is empty")
        encouragement = "Keep going — use the hint to think through the concept again."
        if _hint_reveals_answer(encouragement, correct_answer):
            encouragement = "You are close — review the concept and try again."
        return {
            "hint": hint,
            "encouragement": encouragement,
            "reveals_answer": False,
            "source": source,
        }

    return generate_text_with_providers(
        prompt,
        parse_hint,
        lambda: fallback_hint(topic, question, correct_answer),
    )


def generate_study_plan(
    goal: str,
    grade_level: str,
    available_days: int,
    weak_topics: list[str],
) -> dict:
    weak_list = ", ".join(weak_topics) if weak_topics else "areas from the goal"
    prompt = f"""
Return ONLY valid JSON. No markdown.

{SYSTEM_IDENTITY}

Create a practical day-by-day study plan.

Goal: {goal}
Grade level: {grade_level}
Available days: {available_days}
Weak topics to include: {weak_list}

Requirements:
- Return EXACTLY {available_days} day objects in the days array
- Each day: day number, focus, 2-3 practical tasks, estimated_minutes (30-60)
- Every weak topic must appear in the plan
- Tasks must be specific and actionable

JSON:
{{
  "goal": "{goal}",
  "days": [
    {{
      "day": 1,
      "focus": "specific focus",
      "tasks": ["task 1", "task 2"],
      "estimated_minutes": 45
    }}
  ],
  "source": "openrouter"
}}
"""

    def parse_study_plan(text: str, source: str) -> dict:
        data = _extract_json(text)
        days = _normalize_study_plan_days(
            data.get("days", []),
            available_days,
            goal,
            grade_level,
            weak_topics,
        )
        return StudyPlanResponse(goal=goal, days=days, source=source).model_dump()

    return generate_with_providers(
        prompt,
        parse_study_plan,
        lambda: fallback_study_plan(goal, grade_level, available_days, weak_topics),
    )


def generate_assistant(
    topic: str,
    question: str,
    difficulty: str,
    mode: str,
    student_context: str,
) -> dict:
    prompt = f"""
Return ONLY valid JSON. No markdown.

{SYSTEM_IDENTITY}

Answer the student's question about a STEM topic.
Topic: {topic}
Student question: {question}
Difficulty: {difficulty}
Mode: {mode}
Student context: {student_context}

Requirements:
- answer must be specific to {topic}
- do not give generic study advice unless the topic is vague
- if the student asks only for a homework answer, guide with explanation and hints
- include exactly 3 key_points
- include one real-world example
- include 2-3 next_steps
- include exactly 3 suggested_questions for follow-up
- simple English

JSON:
{{
  "topic": "{topic}",
  "answer": "clear topic-specific answer",
  "key_points": ["point 1", "point 2", "point 3"],
  "example": "real-world example",
  "next_steps": ["step 1", "step 2"],
  "suggested_questions": ["q1", "q2", "q3"],
  "safety_note": "{SAFETY_NOTE}",
  "source": "openrouter"
}}
"""

    def parse_assistant(text: str, source: str) -> dict:
        return _assistant_from_text(text, topic, question, source)

    return generate_with_providers(
        prompt,
        parse_assistant,
        lambda: fallback_assistant(topic, question, difficulty, mode, student_context),
    )


def generate_review_quiz(
    topic: str,
    difficulty: str,
    score: int,
    total: int,
    weak_concepts: list[str],
) -> dict:
    percentage = round((score / total) * 100) if total else 0
    weak_list = ", ".join(weak_concepts) if weak_concepts else f"core ideas of {topic}"
    prompt = f"""
Return ONLY valid JSON. No markdown.

{SYSTEM_IDENTITY}

Review a student's quiz performance.
Topic: {topic}
Difficulty: {difficulty}
Score: {score}/{total} ({percentage}%)
Weak concepts: {weak_list}

JSON:
{{
  "topic": "{topic}",
  "summary": "short encouraging summary",
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["improvement 1", "improvement 2", "improvement 3"],
  "next_steps": ["step 1", "step 2", "step 3"]
}}
"""

    def parse_review(text: str, source: str) -> dict:
        data = _extract_json(text)
        data["source"] = source
        return ReviewQuizResponse(**data).model_dump()

    return generate_with_providers(
        prompt,
        parse_review,
        lambda: fallback_review_quiz(topic, difficulty, score, total, weak_concepts),
    )


def generate_recommend_next(
    topic: str,
    difficulty: str,
    completed_topics: list[str],
    score: int | None,
    total: int | None,
) -> dict:
    completed_list = ", ".join(completed_topics) if completed_topics else "none"
    score_text = f"{score}/{total}" if score is not None and total else "not provided"
    prompt = f"""
Return ONLY valid JSON. No markdown.

{SYSTEM_IDENTITY}

Recommend next STEM topics for a student.
Current topic: {topic}
Difficulty: {difficulty}
Completed topics: {completed_list}
Recent quiz score: {score_text}

JSON:
{{
  "current_topic": "{topic}",
  "recommended_topics": ["topic 1", "topic 2", "topic 3"],
  "reason": "why these topics are good next steps",
  "study_tip": "one practical study tip"
}}
"""

    def parse_recommend(text: str, source: str) -> dict:
        data = _extract_json(text)
        data["source"] = source
        data["recommended_topics"] = (data.get("recommended_topics") or [])[:5]
        return RecommendNextResponse(**data).model_dump()

    return generate_with_providers(
        prompt,
        parse_recommend,
        lambda: fallback_recommend_next(topic, difficulty, completed_topics, score, total),
    )


def generate_scholarship_advice(profile: ScholarshipRequest) -> dict:
    base = fallback_scholarship_match(profile)

    if not get_settings().ai_configured:
        base["source"] = "accessstem_local"
        base["debug_reason"] = "ALL_PROVIDERS_FAILED"
        base["provider_attempts"] = [
            {"provider": provider, "ok": False, "error_code": "NOT_CONFIGURED"}
            for provider in ("cohere", "openrouter", "gemini", "groq")
        ]
        return ScholarshipResponse(**base).model_dump()

    prompt = f"""
Return ONLY valid JSON. No markdown.

You are an ethical scholarship readiness advisor for TUTall.
Use the deterministic matches already calculated.
Do NOT guarantee acceptance.

Student profile:
{profile.model_dump_json(indent=2)}

Matches:
{json.dumps(base["recommended_scholarships"], indent=2)}

Only improve summary, strengths, improvements, and next_steps.
Do not change fit_score or readiness_score.

JSON:
{{
  "summary": "encouraging summary under 80 words",
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["improvement 1", "improvement 2"],
  "next_steps": ["step 1", "step 2", "step 3"]
}}
"""

    def parse_scholarship(text: str, source: str) -> dict:
        ai_data = _extract_json(text)
        result = dict(base)
        result["summary"] = _ensure_no_guarantee(
            ai_data.get("summary", base["summary"])
        )
        result["strengths"] = (ai_data.get("strengths") or base["strengths"])[:4]
        result["improvements"] = (ai_data.get("improvements") or base["improvements"])[:4]
        result["next_steps"] = (ai_data.get("next_steps") or base["next_steps"])[:5]
        result["disclaimer"] = SCHOLARSHIP_DISCLAIMER
        result["source"] = source
        result.pop("debug_reason", None)
        result.pop("provider_attempts", None)
        return ScholarshipResponse(**result).model_dump()

    return generate_with_providers(prompt, parse_scholarship, lambda: base)
