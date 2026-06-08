from app.schemas import (
    SAFETY_NOTE,
    ScholarshipRequest,
    StudyPlanDay,
)


def fallback_explanation(topic: str, difficulty: str, low_bandwidth: bool = False) -> dict:
    if low_bandwidth:
        explanation = (
            f"{topic} is a core STEM idea. Learn the main concept, connect one example, "
            "then answer a short check question."
        )
        key_points = [
            f"Start with the definition of {topic}",
            "Use one real-world example",
            "Practice with a short question",
        ]
    else:
        explanation = (
            f"{topic} can be learned step by step. First, understand the main idea in simple words. "
            "Then connect it to a real example from school, technology, or nature. "
            "Finally, test yourself with a short question to build confidence."
        )
        key_points = [
            f"Define {topic} in your own words",
            "Connect the concept to a real-world example",
            "Practice with hints instead of copying answers",
            "Review mistakes to strengthen understanding",
        ]

    return {
        "topic": topic,
        "level": difficulty,
        "explanation": explanation,
        "example": (
            f"A practical example of {topic} can appear in sports, engineering, medicine, "
            "or everyday problem solving."
        ),
        "key_points": key_points[:4],
        "check_question": f"What is the main idea behind {topic}?",
        "next_topics": [
            f"Applications of {topic}",
            f"Practice problems for {topic}",
        ],
        "safety_note": SAFETY_NOTE,
        "source": "fallback",
    }


def fallback_quiz(topic: str, difficulty: str = "beginner", question_count: int = 5) -> dict:
    base_questions = [
        {
            "id": "q1",
            "question": f"What is the best first step when learning {topic}?",
            "options": [
                "Understand the main idea",
                "Memorize random facts",
                "Skip examples",
                "Avoid practice",
            ],
            "correct_answer": "Understand the main idea",
            "explanation": "Understanding the core idea makes the rest of the topic easier.",
            "concept": "Learning strategy",
        },
        {
            "id": "q2",
            "question": f"Why is practice important for {topic}?",
            "options": [
                "It helps you test understanding",
                "It removes the need to think",
                "It replaces explanations",
                "It is only for exams",
            ],
            "correct_answer": "It helps you test understanding",
            "explanation": "Practice turns passive reading into active learning.",
            "concept": "Active recall",
        },
        {
            "id": "q3",
            "question": "What should you do after a wrong answer?",
            "options": [
                "Use a hint and review the concept",
                "Give up immediately",
                "Ignore the mistake",
                "Only copy the final answer",
            ],
            "correct_answer": "Use a hint and review the concept",
            "explanation": "Hints support learning without giving away the full answer.",
            "concept": "Growth mindset",
        },
        {
            "id": "q4",
            "question": f"How can a real-world example help with {topic}?",
            "options": [
                "It connects ideas to everyday life",
                "It replaces all study",
                "It guarantees a perfect score",
                "It removes the need for notes",
            ],
            "correct_answer": "It connects ideas to everyday life",
            "explanation": "Examples make abstract STEM ideas easier to remember.",
            "concept": "Concept application",
        },
        {
            "id": "q5",
            "question": "What is a good study habit for STEM topics?",
            "options": [
                "Review a little each day",
                "Cram once before a test only",
                "Avoid asking questions",
                "Skip difficult sections forever",
            ],
            "correct_answer": "Review a little each day",
            "explanation": "Short daily review builds long-term understanding.",
            "concept": "Study habits",
        },
        {
            "id": "q6",
            "question": f"When learning {topic}, what helps most?",
            "options": [
                "Breaking the topic into smaller parts",
                "Reading once without practice",
                "Avoiding all mistakes",
                "Memorizing without meaning",
            ],
            "correct_answer": "Breaking the topic into smaller parts",
            "explanation": "Smaller steps reduce overwhelm and improve retention.",
            "concept": "Chunking",
        },
        {
            "id": "q7",
            "question": "Why should students verify important information?",
            "options": [
                "AI support is helpful but not perfect",
                "Teachers never provide guidance",
                "All online answers are always wrong",
                "Verification is never useful",
            ],
            "correct_answer": "AI support is helpful but not perfect",
            "explanation": "Learning tools support study, but students should confirm key facts.",
            "concept": "Information literacy",
        },
    ]

    count = max(3, min(question_count, 7))
    return {
        "topic": topic,
        "level": difficulty,
        "questions": base_questions[:count],
        "source": "fallback",
    }


def fallback_hint(topic: str, question: str, correct_answer: str) -> dict:
    return {
        "hint": (
            f"Focus on the key idea in the question about {topic}. "
            "Eliminate options that do not match the main concept."
        ),
        "encouragement": "You are close — review the concept and try again.",
        "reveals_answer": False,
        "source": "fallback",
    }


def fallback_study_plan(
    goal: str,
    grade_level: str,
    available_days: int,
    weak_topics: list[str],
) -> dict:
    topics = weak_topics or ["core STEM review", "practice problems"]
    days = []

    for day_number in range(1, available_days + 1):
        focus_topic = topics[(day_number - 1) % len(topics)]
        days.append(
            StudyPlanDay(
                day=day_number,
                focus=f"Day {day_number}: {focus_topic}",
                tasks=[
                    f"Review the main idea of {focus_topic}",
                    "Complete 3 practice questions",
                    "Write one sentence explaining what you learned",
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

        matches.append(
            {
                "name": scholarship["name"],
                "category": scholarship["category"],
                "fit_score": fit_score,
                "estimated_amount": scholarship["estimated_amount"],
                "deadline": scholarship["deadline"],
                "strengths": [
                    f"Strong interest in {profile.intended_major}",
                    "Profile can be compared with scholarship requirements",
                ],
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
