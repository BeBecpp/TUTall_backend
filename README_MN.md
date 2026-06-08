# TUTall Backend — Монгол заавар

**TUTall** бол STEM суралцах, quiz, hint, scholarship readiness, progress tracking-ийг дэмждэг AI backend.

**AccessSTEM AI** — гол AI engine. Frontend **хэзээ ч Gemini руу шууд холбогдохгүй**. Бүх AI хүсэлт backend-ээр дамжина.

```text
Flutter / Web Frontend  →  TUTall Backend  →  Gemini AI
                              (API key энд)
                         →  Supabase Postgres (optional)
```

---

## 1. Юу хийсэн бэ?

### Backend бүтэц

| Файл / Folder | Юу хийдэг вэ |
|---------------|--------------|
| `api/index.py` | Vercel serverless entrypoint — `app`-ийг expose хийнэ |
| `app/main.py` | FastAPI app, middleware, router-үүд |
| `app/config.py` | `.env` environment variables уншина |
| `app/ai_engine.py` | Gemini AI дуудлага (google-genai) |
| `app/fallback.py` | AI ажиллахгүй үед demo-safe хариу |
| `app/safety.py` | Prompt injection хамгаалалт |
| `app/rate_limit.py` | IP-ээр rate limiting (40 req/min) |
| `app/storage.py` | Supabase Postgres + in-memory fallback |
| `app/errors.py` | Аюулгүй JSON error format |
| `app/routes/` | API endpoint-үүд |
| `schema.sql` | Supabase table-үүд |
| `tests/` | 29 pytest test (Gemini key шаардлагагүй) |

### Гол feature-үүд

- STEM topic **explain** (тайлбар)
- **Quiz** үүсгэх (3–7 асуулт, 4 сонголт)
- **Hint** (хариу шууд өгөхгүй)
- **Check answer** (Gemini дуудахгүй, deterministic)
- **Study plan** (7 хоногийн төлөвлөгөө)
- **Scholarship match** (readiness score + зөвлөмж)
- **Progress tracking** (student_id-ээр хадгална)

---

## 2. Security — API key хэрхэн хамгаалагдсан бэ?

### Гол зарчим: Proxy pattern

Gemini API key (`GEMINI_API_KEY`) зөвхөн **server дээр** байна:

- Local: `.env` файл
- Production: Vercel Environment Variables

Frontend, Flutter app, GitHub Pages кодонд **хэзээ ч** key оруулахгүй.

```text
❌ БУРУУ:  Flutter → Gemini API (key app дотор)
✅ ЗӨВ:   Flutter → TUTall Backend → Gemini API
```

### Security layer-үүд

| Layer | Юу хийдэг вэ |
|-------|--------------|
| **Environment variables** | Key, DATABASE_URL зөвхөн server-side |
| **CORS** | Зөвхөн зөвшөөрсөн frontend origin-оос request авна |
| **Rate limiting** | IP бүр 40 request/minute (хэт их дуудлага блок) |
| **Prompt injection block** | "ignore previous instructions", "show api key" гэх мэт block |
| **Security headers** | `X-Frame-Options: DENY`, `nosniff`, etc. |
| **Safe errors** | Stack trace, key хэзээ ч client руу очихгүй |
| **Fallback mode** | Key байхгүй ч app унахгүй, demo ажиллана |
| **Hint safety** | AI hint хариуг шууд илрүүлэхгүй |

### Юу frontend руу буцаадаг вэ?

AI endpoint-үүд `source` field буцаана:

| `source` | Утга |
|----------|------|
| `"gemini"` | Жинхэнэ AI хариу |
| `"fallback"` | Offline/demo хариу (key байхгүй эсвэл AI алдаа) |
| `"hybrid"` | Scholarship (deterministic score + AI advice) |

---

## 3. API Endpoint-үүд

**Base URL:**
- Local: `http://127.0.0.1:8000`
- Vercel: `https://YOUR-PROJECT.vercel.app`

| Method | Endpoint | Тайлбар |
|--------|----------|---------|
| GET | `/health` | Backend амьд эсэх шалгах |
| GET | `/api/meta` | API metadata |
| POST | `/api/accessstem/assistant` | AI chatbot / help panel |
| POST | `/api/accessstem/explain` | STEM тайлбар |
| POST | `/api/accessstem/quiz` | Quiz үүсгэх |
| POST | `/api/accessstem/hint` | Hint (хариу өгөхгүй) |
| POST | `/api/accessstem/check-answer` | Хариу шалгах |
| POST | `/api/accessstem/study-plan` | Сургалтын төлөвлөгөө |
| POST | `/api/scholarships/match` | Scholarship readiness |
| POST | `/api/progress` | Progress хадгалах |
| GET | `/api/progress?student_id=` | Progress жагсаах |
| DELETE | `/api/progress?student_id=` | Progress устгах |

Interactive docs: `/docs`

---

## 4. Frontend дээр юу хийх вэ?

### 4.1 Хийх ёстой зүйлс

1. **Backend URL-ээ тохируул**
2. **Dio / fetch** ашиглан backend API дуудах
3. **`student_id`** progress-д илгээ (жишээ: `"demo-user"` эсвэл login user id)
4. Response-ийн **`source`** шалга (gemini vs fallback)
5. Error handling — `error.code`, `error.message` унш

### 4.2 Хийж болохгүй зүйлс

- ❌ `GEMINI_API_KEY` Flutter кодонд оруулах
- ❌ Gemini API шууд дуудах
- ❌ `DATABASE_URL` frontend-д оруулах
- ❌ API key-г `SharedPreferences` / `FlutterSecureStorage`-д хадгалах (key байх ёсгүй!)

---

## 5. Flutter (Dio) integration

### Step 1 — `api_service.dart` base URL

```dart
class ApiService {
  static const String baseUrl = 'https://YOUR-PROJECT.vercel.app';
  // Local test: 'http://10.0.2.2:8000' (Android emulator)
  // Local test: 'http://127.0.0.1:8000' (iOS simulator)

  final Dio _dio = Dio(BaseOptions(
    baseUrl: baseUrl,
    headers: {'Content-Type': 'application/json'},
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 60),
  ));
}
```

### Step 2 — AI Assistant (chat panel)

```dart
Future<Map<String, dynamic>> askAssistant({
  required String topic,
  required String question,
}) async {
  final response = await _dio.post('/api/accessstem/assistant', data: {
    'topic': topic,
    'question': question,
    'difficulty': 'beginner',
    'mode': 'learning',
    'student_context': 'high school student preparing for quiz',
  });
  return response.data;
}
```

### Step 3 — Explain topic

```dart
Future<Map<String, dynamic>> explainTopic(String topic) async {
  final response = await _dio.post('/api/accessstem/explain', data: {
    'topic': topic,
    'difficulty': 'beginner',      // beginner | middle school | high school | advanced
    'low_bandwidth': false,
  });
  return response.data;
}
```

**Response жишээ:**
```json
{
  "topic": "Newton's Laws",
  "level": "beginner",
  "explanation": "...",
  "example": "...",
  "key_points": ["...", "..."],
  "check_question": "...",
  "next_topics": ["...", "..."],
  "safety_note": "AI-generated learning support. Verify important information.",
  "source": "gemini"
}
```

### Step 3 — Quiz

```dart
Future<Map<String, dynamic>> generateQuiz(String topic) async {
  final response = await _dio.post('/api/accessstem/quiz', data: {
    'topic': topic,
    'difficulty': 'middle school',
    'question_count': 5,   // min 3, max 7
  });
  return response.data;
}
```

### Step 4 — Hint

```dart
Future<Map<String, dynamic>> getHint({
  required String topic,
  required String question,
  required String studentAnswer,
  required String correctAnswer,
}) async {
  final response = await _dio.post('/api/accessstem/hint', data: {
    'topic': topic,
    'question': question,
    'student_answer': studentAnswer,
    'correct_answer': correctAnswer,
  });
  return response.data;
}
```

### Step 5 — Check answer (Gemini дуудахгүй)

```dart
Future<Map<String, dynamic>> checkAnswer({
  required String question,
  required String studentAnswer,
  required String correctAnswer,
  String explanation = '',
}) async {
  final response = await _dio.post('/api/accessstem/check-answer', data: {
    'question': question,
    'student_answer': studentAnswer,
    'correct_answer': correctAnswer,
    'explanation': explanation,
  });
  return response.data;
}
```

### Step 6 — Progress хадгалах

```dart
Future<Map<String, dynamic>> saveProgress({
  required String studentId,
  required String topic,
  required int score,
  required int total,
}) async {
  final response = await _dio.post('/api/progress', data: {
    'student_id': studentId,
    'topic': topic,
    'score': score,
    'total': total,
  });
  return response.data;
}

Future<Map<String, dynamic>> getProgress(String studentId) async {
  final response = await _dio.get('/api/progress', queryParameters: {
    'student_id': studentId,
  });
  return response.data;
}
```

### Step 7 — Scholarship match

```dart
Future<Map<String, dynamic>> matchScholarships({
  required String gradeLevel,
  required double gpa,
  required String country,
  required String intendedMajor,
  required String englishLevel,
  String financialNeed = 'medium',
  String activities = '',
  bool hasEssay = false,
  bool hasEnglishTest = false,
}) async {
  final response = await _dio.post('/api/scholarships/match', data: {
    'grade_level': gradeLevel,
    'gpa': gpa,
    'country': country,
    'intended_major': intendedMajor,
    'english_level': englishLevel,
    'financial_need': financialNeed,
    'activities': activities,
    'has_essay': hasEssay,
    'has_english_test': hasEnglishTest,
  });
  return response.data;
}
```

### Step 8 — Error handling

Backend error format:

```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Safe user-facing message",
    "request_id": "uuid"
  }
}
```

```dart
try {
  final data = await explainTopic('Photosynthesis');
} on DioException catch (e) {
  if (e.response?.statusCode == 400) {
    final error = e.response?.data['error'];
    print('Error: ${error['message']}');
  } else if (e.response?.statusCode == 429) {
    print('Rate limit exceeded — retry later');
  }
}
```

---

## 6. Environment variables (.env)

`.env.example`-ийг хуулж `.env` үүсгэ:

```env
APP_NAME=TUTall Backend
APP_ENV=development
GEMINI_API_KEY=your_key_here          # Зөвхөн backend дээр!
GEMINI_MODEL=gemini-1.5-flash
DATABASE_URL=                         # Supabase URI (optional)
ALLOWED_ORIGINS=http://localhost:5500,https://ajays22-orgs.github.io/TUTall
RATE_LIMIT_PER_MINUTE=40
ENABLE_AI=true
```

| Variable | Хаана тавих вэ |
|----------|----------------|
| `GEMINI_API_KEY` | `.env` + Vercel env (frontend биш!) |
| `DATABASE_URL` | `.env` + Vercel env (frontend биш!) |
| `ALLOWED_ORIGINS` | Frontend URL-ээ заавал нэм |

---

## 7. Supabase (Database)

`DATABASE_URL` байвал:
- Progress → `learning_progress` table
- Scholarship → `scholarship_profiles` table
- AI logs → `ai_request_logs` table

`DATABASE_URL` байхгүй бол **in-memory fallback** — demo хэвээр ажиллана.

Supabase connection string:
```text
postgresql://postgres.[REF]:[PASSWORD]@...pooler.supabase.com:6543/postgres
```

---

## 8. Local ажиллуулах

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # GEMINI_API_KEY нэм
python -m uvicorn app.main:app --reload
```

Шалгах:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

Test:
```bash
pytest -v
```

---

## 9. Vercel deploy

1. GitHub руу push
2. vercel.com → Import project
3. Environment Variables нэм:
   - `GEMINI_API_KEY`
   - `DATABASE_URL`
   - `ALLOWED_ORIGINS` (GitHub Pages URL)
   - `APP_ENV=production`
4. Deploy

Entrypoint: `api/index.py` → `from app.main import app`

---

## 10. Frontend checklist (hackathon demo)

- [ ] Backend URL Flutter `api_service.dart`-д тохируулсан
- [ ] Explain screen → `POST /api/accessstem/explain`
- [ ] Quiz screen → `POST /api/accessstem/quiz`
- [ ] Wrong answer → `POST /api/accessstem/hint`
- [ ] Submit answer → `POST /api/accessstem/check-answer`
- [ ] Progress → `POST /api/progress` + `GET /api/progress`
- [ ] Scholarship → `POST /api/scholarships/match`
- [ ] `source: "fallback"` үед UI хэвийн харуулна
- [ ] Gemini key Flutter кодонд **байхгүй**

---

## 11. Түгээмэл асуултууд

**Q: Gemini key байхгүй бол app ажиллах уу?**  
A: Тийм. `source: "fallback"` хариу ирнэ. Demo унахгүй.

**Q: Database байхгүй бол?**  
A: In-memory fallback. Local demo OK, гэхдээ Vercel cold start дээр progress reset болно.

**Q: CORS error гарвал?**  
A: Frontend URL-ээ `ALLOWED_ORIGINS`-д нэм. Vercel env дээр шинэчил.

**Q: 429 error?**  
A: Rate limit (40/min). Хэт олон request илгээж байна.

---

## 12. Холбоотой файлууд

- [README.md](./README.md) — English technical docs
- [curl-tests.md](./curl-tests.md) — API test commands
- [schema.sql](./schema.sql) — Supabase tables

---

**STEMINATE HACKS 2026 — TUTall / AccessSTEM AI**
