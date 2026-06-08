from app.schemas import (
    SAFETY_NOTE,
    ScholarshipRequest,
    StudyPlanDay,
)
from app.topic_knowledge import build_topic_quiz_questions, get_topic_bundle


def fallback_explanation(topic: str, difficulty: str, low_bandwidth: bool = False) -> dict:
    bundle = get_topic_bundle(topic)

    if bundle:
        explanation = bundle["explanation"]
        if low_bandwidth:
            explanation = explanation.split(". ")[0] + "."
        return {
            "topic": topic,
            "level": difficulty,
            "explanation": explanation,
            "example": bundle["example"],
            "key_points": bundle["key_points"][:3],
            "check_question": bundle["check_question"],
            "next_topics": bundle["next_topics"][:2],
            "safety_note": SAFETY_NOTE,
            "source": "fallback",
        }

    return {
        "topic": topic,
        "level": difficulty,
        "explanation": (
            f"{topic} is an important STEM topic at the {difficulty} level. "
            f"Start with a clear definition of {topic}, connect it to one real example, "
            "then practice with short questions to check your understanding."
        ),
        "example": (
            f"You can find real-world uses of {topic} in science class, technology, "
            "engineering projects, or everyday problem solving."
        ),
        "key_points": [
            f"Define {topic} in simple words",
            f"Connect {topic} to one real-world example",
            f"Practice {topic} with questions and hints",
        ],
        "check_question": f"What is the main idea behind {topic}?",
        "next_topics": [
            f"Applications of {topic}",
            f"Practice problems for {topic}",
        ],
        "safety_note": SAFETY_NOTE,
        "source": "fallback",
    }


def fallback_quiz(topic: str, difficulty: str = "beginner", question_count: int = 5) -> dict:
    count = max(3, min(question_count, 7))
    questions = build_topic_quiz_questions(topic, count)
    return {
        "topic": topic,
        "level": difficulty,
        "questions": questions,
        "source": "fallback",
    }


def fallback_hint(topic: str, question: str, correct_answer: str) -> dict:
    bundle = get_topic_bundle(topic)
    hint = (
        f"Re-read the question about {topic} and identify which concept it is testing. "
        "Eliminate options that do not match that concept."
    )
    if bundle and bundle.get("key_points"):
        hint = (
            f"Think about this key idea for {topic}: {bundle['key_points'][0]}. "
            "Then compare each option to that idea."
        )

    return {
        "hint": hint,
        "encouragement": "You are closer than you think — review the concept and try again.",
        "reveals_answer": False,
        "source": "fallback",
    }


def fallback_assistant(
    topic: str,
    question: str,
    difficulty: str,
    mode: str,
    student_context: str,
) -> dict:
    bundle = get_topic_bundle(topic)

    if bundle:
        answer = bundle["explanation"]
        if "example" in question.lower():
            answer = (
                f"{bundle['explanation']} Example: {bundle['example']}"
            )
        key_points = bundle["key_points"][:3]
        example = bundle["example"]
        next_steps = [
            f"Review the key ideas of {topic}",
            f"Try a short quiz on {topic}",
            "Explain the concept in your own words",
        ]
        suggested = [
            f"Can you give another example of {topic}?",
            f"What is a common mistake students make with {topic}?",
            f"How does {topic} connect to everyday life?",
        ]
    else:
        answer = (
            f"For {topic} at the {difficulty} level: focus on the definition, "
            f"one real example, and a short practice question. "
            f"Your question was: {question}"
        )
        key_points = [
            f"Define {topic} clearly",
            f"Use one example to understand {topic}",
            "Practice with hints instead of copying answers",
        ]
        example = f"A real-world example helps make {topic} easier to understand."
        next_steps = [
            f"Write a one-sentence summary of {topic}",
            f"Complete 3 practice questions on {topic}",
            "Review any mistakes with a hint",
        ]
        suggested = [
            f"What should I study next after {topic}?",
            f"Can you quiz me on {topic}?",
            f"How do I know if I understand {topic}?",
        ]

    if mode == "quiz":
        answer = (
            f"To prepare for a {topic} quiz, review definitions, work through examples, "
            "and practice explaining each concept without looking at notes."
        )

    _ = student_context
    return {
        "topic": topic,
        "answer": answer,
        "key_points": key_points,
        "example": example,
        "next_steps": next_steps,
        "suggested_questions": suggested,
        "safety_note": SAFETY_NOTE,
        "source": "fallback",
    }


def fallback_study_plan(
    goal: str,
    grade_level: str,
    available_days: int,
    weak_topics: list[str],
) -> dict:
    topics = weak_topics or [goal]
    days = []

    for day_number in range(1, available_days + 1):
        focus_topic = topics[(day_number - 1) % len(topics)]
        days.append(
            StudyPlanDay(
                day=day_number,
                focus=f"Day {day_number}: Strengthen {focus_topic}",
                tasks=[
                    f"Review notes and definitions for {focus_topic}",
                    f"Solve 3 practice problems on {focus_topic}",
                    "Write one sentence explaining what you learned today",
                ],
                estimated_minutes=45,
            ).model_dump()
        )

    return {
        "goal": goal,
        "days": days,
        "source": "fallback",
    }


def calculate_scholarship_fit(profile: ScholarshipRequest, scholarship: dict) -> int:
    score = 20

    if profile.gpa >= scholarship["min_gpa"]:
        score += 25
    elif profile.gpa >= scholarship["min_gpa"] - 0.3:
        score += 15

    major = profile.intended_major.lower()
    category = scholarship["category"].lower()
    if category in ("any", "stem") or category in major:
        score += 20

    if profile.financial_need == "high":
        score += 10

    if profile.english_level.strip():
        score += 10

    if profile.activities.strip():
        score += 10

    if profile.has_essay:
        score += 3

    if profile.has_english_test:
        score += 2

    return min(score, 100)


def fallback_scholarship_match(profile: ScholarshipRequest) -> dict:
    catalog = [
        {
            "name": "STEM Future Grant",
            "category": "STEM",
            "min_gpa": 3.5,
            "estimated_amount": 5000,
            "deadline": "2026-07-15",
            "required_documents": ["Transcript", "Personal statement", "Recommendation letter"],
        },
        {
            "name": "Global Access Scholarship",
            "category": "Any",
            "min_gpa": 3.2,
            "estimated_amount": 10000,
            "deadline": "2026-08-01",
            "required_documents": ["Transcript", "Financial need statement", "ID document"],
        },
        {
            "name": "Tech Learners Award",
            "category": "Computer Science",
            "min_gpa": 3.4,
            "estimated_amount": 7000,
            "deadline": "2026-09-10",
            "required_documents": ["Transcript", "Project portfolio", "Recommendation letter"],
        },
    ]

    matches = []
    for scholarship in catalog:
        fit_score = calculate_scholarship_fit(profile, scholarship)
        improvements = ["Verify official eligibility requirements on the scholarship website"]

        if profile.gpa < scholarship["min_gpa"]:
            improvements.append("Improve GPA or target scholarships with lower GPA requirements")
        if not profile.has_essay:
            improvements.append("Prepare a personal statement")
        if not profile.has_english_test:
            improvements.append("Prepare English test proof if required")
        if not profile.activities.strip():
            improvements.append("Add extracurricular or STEM project experience")

        strengths = [f"Interest in {profile.intended_major}"]
        if profile.gpa >= scholarship["min_gpa"]:
            strengths.append("GPA meets or is close to this scholarship range")
        if profile.activities.strip():
            strengths.append("Activities show engagement beyond grades")

        matches.append(
            {
                "name": scholarship["name"],
                "category": scholarship["category"],
                "fit_score": fit_score,
                "estimated_amount": scholarship["estimated_amount"],
                "deadline": scholarship["deadline"],
                "strengths": strengths[:3],
                "improvements": improvements[:4],
                "required_documents": scholarship["required_documents"],
            }
        )

    overall = round(sum(match["fit_score"] for match in matches) / len(matches))

    return {
        "profile_summary": (
            f"Grade {profile.grade_level} student from {profile.country} interested in "
            f"{profile.intended_major} with GPA {profile.gpa}."
        ),
        "overall_readiness_score": overall,
        "matches": matches,
        "advisor": {
            "summary": (
                "These are estimated scholarship readiness matches. TUTall helps you prepare, "
                "but does not guarantee acceptance."
            ),
            "next_steps": [
                "Prepare transcript",
                "Start personal statement",
                "Check official deadlines",
                "Request recommendation letters early",
            ],
            "warning": "This is an estimate and does not guarantee acceptance.",
        },
        "source": "fallback",
    }
