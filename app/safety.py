import re

from fastapi import HTTPException, status

from app.config import get_settings

INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal system prompt",
    "show system prompt",
    "show api key",
    "reveal api key",
    "print api key",
    "print environment variables",
    "show environment variables",
    "bypass safety",
    "act as admin",
    "jailbreak",
    "developer message",
    "system prompt",
]

SECRET_PATTERNS = [
    r"\bapi\s*key\b",
    r"\bsecret\s*key\b",
    r"\bpassword\b",
    r"\btoken\b",
    r"\benvironment\s*variable",
]


def sanitize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def validate_topic(topic: str) -> str:
    cleaned = sanitize_text(topic)
    settings = get_settings()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BAD_REQUEST",
                "message": "Topic cannot be empty.",
            },
        )

    if len(cleaned) > settings.max_topic_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BAD_REQUEST",
                "message": f"Topic must be {settings.max_topic_length} characters or fewer.",
            },
        )

    check_text_safety(cleaned, "topic")
    return cleaned


def validate_text_field(text: str, field_name: str) -> str:
    cleaned = sanitize_text(text)
    settings = get_settings()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BAD_REQUEST",
                "message": f"{field_name} cannot be empty.",
            },
        )

    if len(cleaned) > settings.max_text_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BAD_REQUEST",
                "message": f"{field_name} must be {settings.max_text_length} characters or fewer.",
            },
        )

    check_text_safety(cleaned, field_name)
    return cleaned


def check_text_safety(text: str, field_name: str = "input") -> None:
    lowered = text.lower()

    for phrase in INJECTION_PHRASES:
        if phrase in lowered:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "BAD_REQUEST",
                    "message": f"Unsafe or suspicious content detected in {field_name}.",
                },
            )

    for pattern in SECRET_PATTERNS:
        if re.search(pattern, lowered) and any(
            verb in lowered
            for verb in ("show", "reveal", "print", "give", "tell", "share", "display")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "BAD_REQUEST",
                    "message": "Requests for secrets or credentials are not allowed.",
                },
            )


def check_payload_safety(payload: dict) -> None:
    for key, value in payload.items():
        if isinstance(value, str) and value.strip():
            check_text_safety(value, key)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    check_text_safety(item, key)
