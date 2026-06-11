from app.schemas import ScholarshipRequest
from app.storage import Storage


def test_in_memory_save_and_list_progress():
    storage = Storage(force_memory=True)
    saved = storage.save_progress("student-1", "Algebra", 4, 5)
    assert saved.saved is True
    assert saved.percentage == 80
    assert saved.student_id == "student-1"

    listed = storage.list_progress("student-1")
    assert len(listed.items) == 1
    assert listed.average_percentage == 80


def test_in_memory_dashboard():
    storage = Storage(force_memory=True)
    storage.save_progress("student-dashboard", "Photosynthesis", 4, 5)
    dashboard = storage.get_dashboard("student-dashboard")
    assert dashboard.student_id == "student-dashboard"
    assert dashboard.quizzes_taken == 1
    assert dashboard.last_topic == "Photosynthesis"
    assert dashboard.recommended_next_topic


def test_in_memory_clear_progress():
    storage = Storage(force_memory=True)
    storage.save_progress("student-2", "Physics", 3, 5)
    cleared = storage.clear_progress("student-2")
    assert cleared["deleted"] is True
    assert storage.list_progress("student-2").items == []


def test_in_memory_save_scholarship_profile():
    storage = Storage(force_memory=True)
    profile = ScholarshipRequest(
        grade_level="11",
        gpa=3.8,
        country="Mongolia",
        intended_major="Computer Science",
        english_level="B2",
        financial_need="high",
        activities="Coding club",
        has_essay=False,
        has_english_test=False,
    )
    storage.save_scholarship_profile(profile, 78)
    storage.log_ai_request(
        endpoint="/api/scholarships/match",
        topic="Computer Science",
        source="accessstem_local",
        success=True,
    )


def test_init_db_without_database_url():
    storage = Storage(force_memory=True)
    assert storage.init_db() is True
