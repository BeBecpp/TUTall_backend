# TUTall Backend — cURL Test Commands

Replace `BASE_URL` with your local or deployed backend URL.

- Local: `http://127.0.0.1:8000`
- Vercel: `https://YOUR-PROJECT.vercel.app`

---

## Health

```bash
curl -s "$BASE_URL/health" | jq
```

## API Meta

```bash
curl -s "$BASE_URL/api/meta" | jq
```

## STEM Explanation

```bash
curl -s -X POST "$BASE_URL/api/accessstem/explain" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Newton'\''s Laws",
    "difficulty": "beginner",
    "low_bandwidth": false
  }' | jq
```

## Quiz Generation

```bash
curl -s -X POST "$BASE_URL/api/accessstem/quiz" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Photosynthesis",
    "difficulty": "middle school",
    "question_count": 5
  }' | jq
```

## Hint Mode

```bash
curl -s -X POST "$BASE_URL/api/accessstem/hint" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Newton'\''s Laws",
    "question": "What does Newton'\''s First Law describe?",
    "student_answer": "Gravity",
    "correct_answer": "Objects stay at rest or in motion unless acted on by force"
  }' | jq
```

## Check Answer

```bash
curl -s -X POST "$BASE_URL/api/accessstem/check-answer" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is 2+2?",
    "student_answer": "4",
    "correct_answer": "4",
    "explanation": "Basic addition."
  }' | jq
```

## Study Plan

```bash
curl -s -X POST "$BASE_URL/api/accessstem/study-plan" \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Improve algebra and physics",
    "grade_level": "high school",
    "available_days": 7,
    "weak_topics": ["linear equations", "forces"]
  }' | jq
```

## Scholarship Match

```bash
curl -s -X POST "$BASE_URL/api/scholarships/match" \
  -H "Content-Type: application/json" \
  -d '{
    "grade_level": "11",
    "gpa": 3.8,
    "country": "Mongolia",
    "intended_major": "Computer Science",
    "english_level": "B2",
    "financial_need": "high",
    "activities": "Hackathons, coding club, volunteer teaching",
    "has_essay": false,
    "has_english_test": false
  }' | jq
```

## Progress — Save

```bash
curl -s -X POST "$BASE_URL/api/progress" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "demo-user",
    "topic": "Newton'\''s Laws",
    "score": 4,
    "total": 5
  }' | jq
```

## Progress — List

```bash
curl -s "$BASE_URL/api/progress?student_id=demo-user" | jq
```

## Progress — Delete

```bash
curl -s -X DELETE "$BASE_URL/api/progress?student_id=demo-user" | jq
```

---

## Quick Local Test Script

```bash
export BASE_URL=http://127.0.0.1:8000
curl -s "$BASE_URL/health"
```
