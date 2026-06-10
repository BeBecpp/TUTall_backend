"""Storage layer — Supabase Postgres with in-memory fallback."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.config import get_settings
from app.schemas import ProgressItem, ProgressListResponse, ProgressSaveResponse, ScholarshipRequest

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    def init_db(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def save_progress(
        self,
        student_id: str,
        topic: str,
        score: int,
        total: int,
    ) -> ProgressSaveResponse:
        raise NotImplementedError

    @abstractmethod
    def list_progress(self, student_id: str) -> ProgressListResponse:
        raise NotImplementedError

    @abstractmethod
    def clear_progress(self, student_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def save_scholarship_profile(self, profile: ScholarshipRequest, readiness_score: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def log_ai_request(
        self,
        endpoint: str,
        topic: str | None,
        source: str,
        success: bool,
        error_code: str | None = None,
    ) -> None:
        raise NotImplementedError


class InMemoryBackend(StorageBackend):
    """Fallback store when DATABASE_URL is missing or Postgres is unavailable."""

    def __init__(self) -> None:
        self._progress: list[dict[str, Any]] = []
        self._scholarship_profiles: list[dict[str, Any]] = []
        self._ai_logs: list[dict[str, Any]] = []
        self._lock = Lock()

    def init_db(self) -> bool:
        return True

    def _ensure_student(self, student_id: str) -> None:
        _ = student_id

    def save_progress(
        self,
        student_id: str,
        topic: str,
        score: int,
        total: int,
    ) -> ProgressSaveResponse:
        percentage = round((score / total) * 100) if total > 0 else 0
        item = ProgressItem(
            id=str(uuid.uuid4()),
            student_id=student_id,
            topic=topic,
            score=score,
            total=total,
            percentage=percentage,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._progress.append(item.model_dump())
        return ProgressSaveResponse(saved=True, item=item)

    def list_progress(self, student_id: str) -> ProgressListResponse:
        with self._lock:
            items = [
                ProgressItem(**record)
                for record in self._progress
                if record["student_id"] == student_id
            ]
        items.sort(key=lambda entry: entry.created_at, reverse=True)
        average = round(sum(entry.percentage for entry in items) / len(items)) if items else 0
        return ProgressListResponse(
            student_id=student_id,
            items=items,
            average_percentage=average,
            completed_topics=len(items),
        )

    def clear_progress(self, student_id: str) -> dict:
        with self._lock:
            self._progress = [
                record for record in self._progress if record["student_id"] != student_id
            ]
        return {"deleted": True, "student_id": student_id}

    def save_scholarship_profile(self, profile: ScholarshipRequest, readiness_score: int) -> None:
        with self._lock:
            self._scholarship_profiles.append(
                {
                    "id": str(uuid.uuid4()),
                    "profile": profile.model_dump(),
                    "readiness_score": readiness_score,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    def log_ai_request(
        self,
        endpoint: str,
        topic: str | None,
        source: str,
        success: bool,
        error_code: str | None = None,
    ) -> None:
        with self._lock:
            self._ai_logs.append(
                {
                    "id": str(uuid.uuid4()),
                    "endpoint": endpoint,
                    "topic": topic,
                    "source": source,
                    "success": success,
                    "error_code": error_code,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )


class PostgresBackend(StorageBackend):
    """Supabase Postgres backend using psycopg."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):
        import psycopg

        return psycopg.connect(self._database_url)

    def init_db(self) -> bool:
        """Verify Postgres connectivity. Tables are managed in Supabase."""
        with self._connect() as conn:
            conn.execute("SELECT 1")
            conn.commit()
        logger.info("Database connection verified")
        return True

    def _ensure_student(self, cur, student_id: str) -> None:
        cur.execute(
            """
            INSERT INTO students (external_id)
            VALUES (%s)
            ON CONFLICT (external_id) DO NOTHING
            """,
            (student_id,),
        )

    def save_progress(
        self,
        student_id: str,
        topic: str,
        score: int,
        total: int,
    ) -> ProgressSaveResponse:
        percentage = round((score / total) * 100) if total > 0 else 0
        progress_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_student(cur, student_id)
                cur.execute(
                    """
                    INSERT INTO learning_progress
                        (id, student_id, topic, score, total, percentage, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (
                        progress_id,
                        student_id,
                        topic,
                        score,
                        total,
                        percentage,
                        created_at,
                    ),
                )
                row = cur.fetchone()
            conn.commit()

        item = ProgressItem(
            id=str(row[0]),
            student_id=student_id,
            topic=topic,
            score=score,
            total=total,
            percentage=percentage,
            created_at=row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1]),
        )
        return ProgressSaveResponse(saved=True, item=item)

    def list_progress(self, student_id: str) -> ProgressListResponse:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, student_id, topic, score, total, percentage, created_at
                    FROM learning_progress
                    WHERE student_id = %s
                    ORDER BY created_at DESC
                    LIMIT 100
                    """,
                    (student_id,),
                )
                rows = cur.fetchall()

        items = [
            ProgressItem(
                id=str(row[0]),
                student_id=row[1],
                topic=row[2],
                score=row[3],
                total=row[4],
                percentage=row[5],
                created_at=row[6].isoformat() if hasattr(row[6], "isoformat") else str(row[6]),
            )
            for row in rows
        ]
        average = round(sum(entry.percentage for entry in items) / len(items)) if items else 0
        return ProgressListResponse(
            student_id=student_id,
            items=items,
            average_percentage=average,
            completed_topics=len(items),
        )

    def clear_progress(self, student_id: str) -> dict:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM learning_progress WHERE student_id = %s",
                    (student_id,),
                )
            conn.commit()
        return {"deleted": True, "student_id": student_id}

    def save_scholarship_profile(self, profile: ScholarshipRequest, readiness_score: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO scholarship_profiles (
                        grade_level, gpa, country, intended_major, english_level,
                        financial_need, activities, has_essay, has_english_test, readiness_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        profile.grade_level,
                        profile.gpa,
                        profile.country,
                        profile.intended_major,
                        profile.english_level,
                        profile.financial_need,
                        profile.activities,
                        profile.has_essay,
                        profile.has_english_test,
                        readiness_score,
                    ),
                )
            conn.commit()

    def log_ai_request(
        self,
        endpoint: str,
        topic: str | None,
        source: str,
        success: bool,
        error_code: str | None = None,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ai_request_logs
                        (endpoint, topic, source, success, error_code)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (endpoint, topic, source, success, error_code),
                )
            conn.commit()


class Storage:
    """Resilient facade: Postgres when configured, in-memory fallback on failure."""

    def __init__(self, force_memory: bool = False) -> None:
        settings = get_settings()
        self._memory = InMemoryBackend()
        self._postgres: PostgresBackend | None = None
        self._postgres_enabled = False

        if not force_memory and settings.database_configured:
            try:
                import psycopg  # noqa: F401

                self._postgres = PostgresBackend(settings.database_url)
                self._postgres_enabled = True
            except Exception as exc:
                logger.warning(
                    "Postgres storage unavailable; using in-memory fallback (%s)",
                    type(exc).__name__,
                )

    @property
    def database_enabled(self) -> bool:
        return self._postgres_enabled

    def init_db(self) -> bool:
        if not self._postgres:
            return self._memory.init_db()
        try:
            return self._postgres.init_db()
        except Exception as exc:
            logger.warning("Database init failed; continuing with fallback (%s)", type(exc).__name__)
            self._postgres_enabled = False
            return False

    def save_progress(
        self,
        student_id: str,
        topic: str,
        score: int,
        total: int,
    ) -> ProgressSaveResponse:
        if self._postgres_enabled and self._postgres:
            try:
                return self._postgres.save_progress(student_id, topic, score, total)
            except Exception as exc:
                logger.warning("Progress save failed in Postgres (%s)", type(exc).__name__)
                self._postgres_enabled = False
        return self._memory.save_progress(student_id, topic, score, total)

    def list_progress(self, student_id: str) -> ProgressListResponse:
        if self._postgres_enabled and self._postgres:
            try:
                return self._postgres.list_progress(student_id)
            except Exception as exc:
                logger.warning("Progress list failed in Postgres (%s)", type(exc).__name__)
                self._postgres_enabled = False
        return self._memory.list_progress(student_id)

    def clear_progress(self, student_id: str) -> dict:
        if self._postgres_enabled and self._postgres:
            try:
                return self._postgres.clear_progress(student_id)
            except Exception as exc:
                logger.warning("Progress clear failed in Postgres (%s)", type(exc).__name__)
                self._postgres_enabled = False
        return self._memory.clear_progress(student_id)

    def save_scholarship_profile(self, profile: ScholarshipRequest, readiness_score: int) -> None:
        if self._postgres_enabled and self._postgres:
            try:
                self._postgres.save_scholarship_profile(profile, readiness_score)
                return
            except Exception as exc:
                logger.warning(
                    "Scholarship profile save failed in Postgres (%s)",
                    type(exc).__name__,
                )
                self._postgres_enabled = False
        self._memory.save_scholarship_profile(profile, readiness_score)

    def log_ai_request(
        self,
        endpoint: str,
        topic: str | None,
        source: str,
        success: bool,
        error_code: str | None = None,
    ) -> None:
        if self._postgres_enabled and self._postgres:
            try:
                self._postgres.log_ai_request(endpoint, topic, source, success, error_code)
                return
            except Exception as exc:
                logger.warning("AI request log failed in Postgres (%s)", type(exc).__name__)
                self._postgres_enabled = False
        self._memory.log_ai_request(endpoint, topic, source, success, error_code)


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage


def init_db() -> bool:
    return get_storage().init_db()


def reset_storage(force_memory: bool = True) -> None:
    """Reset storage singleton — tests always use in-memory mode."""
    global _storage
    _storage = Storage(force_memory=force_memory)


# Backward-compatible helpers used by older code/tests.
def get_progress_repository() -> Storage:
    return get_storage()


def reset_progress_repository() -> None:
    reset_storage(force_memory=True)
