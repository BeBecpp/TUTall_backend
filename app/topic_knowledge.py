"""Curated topic bundles for high-quality fallback when Gemini is unavailable."""

from __future__ import annotations

import re
from typing import Any


def _normalize_key(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", topic.lower()).strip()


TOPIC_BUNDLES: dict[str, dict[str, Any]] = {
    "newton s laws": {
        "explanation": (
            "Newton's three laws describe how forces change motion. "
            "The first law says objects keep their motion unless a net force acts. "
            "The second law links force, mass, and acceleration (F = ma). "
            "The third law says every action has an equal and opposite reaction."
        ),
        "example": "A passenger lurches forward when a bus brakes suddenly — inertia resists the change in motion.",
        "key_points": [
            "First law: inertia and balanced forces",
            "Second law: F = ma connects force and acceleration",
            "Third law: action-reaction force pairs",
        ],
        "check_question": "What does Newton's second law relate force to?",
        "next_topics": ["Friction and net force", "Free-body diagrams"],
        "quiz": [
            {
                "question": "What does Newton's First Law describe?",
                "options": [
                    "Objects resist changes in motion",
                    "Force equals mass times velocity",
                    "Gravity pulls everything down",
                    "Energy cannot be created",
                ],
                "correct_answer": "Objects resist changes in motion",
                "explanation": "The first law is about inertia — objects keep moving or staying still unless a net force acts.",
                "concept": "Inertia",
            },
            {
                "question": "Newton's Second Law is written as:",
                "options": ["F = ma", "E = mc²", "V = IR", "P = IV"],
                "correct_answer": "F = ma",
                "explanation": "Force equals mass times acceleration.",
                "concept": "F = ma",
            },
            {
                "question": "When you push a wall, the wall pushes back. This illustrates:",
                "options": [
                    "Newton's Third Law",
                    "Newton's First Law",
                    "Conservation of mass",
                    "Ohm's Law",
                ],
                "correct_answer": "Newton's Third Law",
                "explanation": "Action and reaction forces occur in pairs on different objects.",
                "concept": "Action-reaction",
            },
            {
                "question": "A book at rest on a table stays at rest because:",
                "options": [
                    "Forces are balanced",
                    "No gravity acts on it",
                    "Mass is zero",
                    "Friction is infinite",
                ],
                "correct_answer": "Forces are balanced",
                "explanation": "Gravity and the normal force cancel, so net force is zero.",
                "concept": "Equilibrium",
            },
            {
                "question": "Doubling the mass of an object (same force) will:",
                "options": [
                    "Reduce acceleration",
                    "Double acceleration",
                    "Stop motion",
                    "Remove friction",
                ],
                "correct_answer": "Reduce acceleration",
                "explanation": "From F = ma, larger mass means smaller acceleration for the same force.",
                "concept": "Mass and acceleration",
            },
        ],
    },
    "photosynthesis": {
        "explanation": (
            "Photosynthesis is how green plants make food using sunlight. "
            "In chloroplasts, light energy converts carbon dioxide and water into glucose and oxygen. "
            "It powers most life on Earth by producing food and oxygen."
        ),
        "example": "Leaves use sunlight to grow — that growth depends on glucose made during photosynthesis.",
        "key_points": [
            "Occurs in chloroplasts using chlorophyll",
            "Inputs: CO₂, water, light",
            "Outputs: glucose and oxygen",
        ],
        "check_question": "What gas do plants release during photosynthesis?",
        "next_topics": ["Cellular respiration", "Plant cell structure"],
        "quiz": [
            {
                "question": "Where does photosynthesis mainly occur in a plant cell?",
                "options": ["Chloroplasts", "Mitochondria", "Nucleus", "Ribosomes"],
                "correct_answer": "Chloroplasts",
                "explanation": "Chloroplasts contain chlorophyll for capturing light.",
                "concept": "Chloroplasts",
            },
            {
                "question": "Which gas do plants take in for photosynthesis?",
                "options": ["Carbon dioxide", "Nitrogen", "Helium", "Methane"],
                "correct_answer": "Carbon dioxide",
                "explanation": "CO₂ is a key reactant in photosynthesis.",
                "concept": "Reactants",
            },
            {
                "question": "What energy source drives photosynthesis?",
                "options": ["Sunlight", "Heat from soil", "Wind", "Sound"],
                "correct_answer": "Sunlight",
                "explanation": "Light energy is converted into chemical energy in glucose.",
                "concept": "Light energy",
            },
            {
                "question": "A main product of photosynthesis is:",
                "options": ["Glucose", "Salt", "Iron", "Plastic"],
                "correct_answer": "Glucose",
                "explanation": "Plants store chemical energy as glucose.",
                "concept": "Products",
            },
            {
                "question": "Which pigment captures light in plants?",
                "options": ["Chlorophyll", "Hemoglobin", "Melanin", "Keratin"],
                "correct_answer": "Chlorophyll",
                "explanation": "Chlorophyll gives leaves their green color and absorbs light.",
                "concept": "Chlorophyll",
            },
        ],
    },
}


def get_topic_bundle(topic: str) -> dict[str, Any] | None:
    key = _normalize_key(topic)
    if key in TOPIC_BUNDLES:
        return TOPIC_BUNDLES[key]
    for bundle_key, bundle in TOPIC_BUNDLES.items():
        if bundle_key in key or key in bundle_key:
            return bundle
    return None


def build_topic_quiz_questions(topic: str, question_count: int, start_id: int = 1) -> list[dict[str, Any]]:
    """Build topic-aware quiz questions for fallback or repair."""
    bundle = get_topic_bundle(topic)
    questions: list[dict[str, Any]] = []

    if bundle and bundle.get("quiz"):
        for index, item in enumerate(bundle["quiz"][:question_count], start=start_id):
            questions.append({**item, "id": f"q{index}"})

    templates = [
        {
            "question": f"Which statement best describes {topic}?",
            "options": [
                f"It is a core concept students study in STEM classes about {topic}",
                f"{topic} has no connection to science",
                f"{topic} is only memorization with no real meaning",
                f"{topic} cannot be practiced or tested",
            ],
            "correct_answer": f"It is a core concept students study in STEM classes about {topic}",
            "explanation": f"Understanding {topic} means learning definitions, examples, and practice problems.",
            "concept": topic,
        },
        {
            "question": f"What is a good first step to master {topic}?",
            "options": [
                "Learn the definition and one real example",
                "Skip all practice questions",
                "Memorize unrelated facts",
                "Avoid reviewing mistakes",
            ],
            "correct_answer": "Learn the definition and one real example",
            "explanation": f"A clear definition and example make {topic} easier to remember.",
            "concept": "Study strategy",
        },
        {
            "question": f"Why is practice important when studying {topic}?",
            "options": [
                "It checks whether you truly understand the concept",
                "It replaces the need to read",
                "It guarantees a perfect exam score",
                "It removes the need for hints",
            ],
            "correct_answer": "It checks whether you truly understand the concept",
            "explanation": f"Practice reveals gaps in your understanding of {topic}.",
            "concept": "Active learning",
        },
        {
            "question": f"How can a real-world example help with {topic}?",
            "options": [
                "It connects abstract ideas to everyday life",
                "It makes the topic impossible to learn",
                "It replaces all formulas",
                "It removes the need for notes",
            ],
            "correct_answer": "It connects abstract ideas to everyday life",
            "explanation": f"Examples make {topic} more concrete and memorable.",
            "concept": "Application",
        },
        {
            "question": f"When stuck on a {topic} problem, what should you try first?",
            "options": [
                "Identify the key concept the question is testing",
                "Copy an answer without thinking",
                "Skip the topic forever",
                "Ignore the question wording",
            ],
            "correct_answer": "Identify the key concept the question is testing",
            "explanation": f"Finding the core concept helps you choose the right approach for {topic}.",
            "concept": "Problem solving",
        },
        {
            "question": f"Which resource is most useful for reviewing {topic}?",
            "options": [
                "Notes, examples, and practice questions on the topic",
                "Random unrelated videos only",
                "Guessing on every question",
                "Avoiding all feedback",
            ],
            "correct_answer": "Notes, examples, and practice questions on the topic",
            "explanation": f"Focused review materials directly support mastery of {topic}.",
            "concept": "Review",
        },
        {
            "question": f"What does it mean to explain {topic} in your own words?",
            "options": [
                "You can describe the idea without copying textbook text",
                "You must memorize every word exactly",
                "You should avoid using examples",
                "You never need to practice",
            ],
            "correct_answer": "You can describe the idea without copying textbook text",
            "explanation": f"Explaining {topic} in your own words shows real understanding.",
            "concept": "Comprehension",
        },
    ]

    next_id = len(questions) + start_id
    for template in templates:
        if len(questions) >= question_count:
            break
        questions.append({**template, "id": f"q{next_id}"})
        next_id += 1

    return questions[:question_count]
