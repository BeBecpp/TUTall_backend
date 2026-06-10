# TUTall Backend


Production-ready FastAPI backend for **TUTall**, an AI-powered student support platform built for **STEMINATE HACKS 2026** under the theme **AI for a Better World**.

The core engine is **AccessSTEM AI** — a secure learning assistant that helps students with STEM explanations, quizzes, guided hints, study plans, scholarship readiness, and progress tracking.

## Product Summary

TUTall focuses on **Community & Access** and education equity. The frontend never calls Gemini directly. All AI requests flow through this backend:

```text
Frontend → TUTall Backend → Cohere/OpenRouter/Gemini/Groq → TUTall Backend → Frontend
```

AI provider chain: **Cohere → OpenRouter → Gemini → Groq → AccessSTEM Local Engine**. If live providers fail, the backend uses the built-in local engine safely without exposing API keys or raw provider errors.

## Architecture

```text
api/index.py          # Vercel serverless entrypoint
app/main.py           # FastAPI app, middleware, routers
app/config.py         # Environment settings
app/providers.py      # OpenRouter provider client
app/ai_engine.py      # AccessSTEM AI generation logic
app/fallback.py       # AccessSTEM local engine responses
app/safety.py         # Input validation & prompt-injection defense
app/rate_limit.py     # In-memory IP rate limiting
app/storage.py        # Swappable in-memory progress store
app/errors.py         # Safe JSON error responses
app/routes/           # API route modules
tests/                # Pytest suite (no Gemini key required)
```

### Middleware Stack

1. **Request ID** — `X-Request-ID` on every response
2. **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, etc.
3. **Rate limiting** — 40 requests/minute per IP (configurable)
4. **CORS** — Frontend origins from `ALLOWED_ORIGINS`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service welcome |
| `GET` | `/health` | Health check |
| `GET` | `/api/ai/status` | AI provider status (no secrets) |
| `GET` | `/api/meta` | Public API metadata |
| `POST` | `/api/accessstem/assistant` | AI chatbot / help panel |
| `POST` | `/api/accessstem/explain` | STEM topic explanation |
| `POST` | `/api/accessstem/quiz` | Multiple-choice quiz |
| `POST` | `/api/accessstem/hint` | Guided hint (no answer reveal) |
| `POST` | `/api/accessstem/check-answer` | Deterministic answer check |
| `POST` | `/api/accessstem/study-plan` | Personalized study plan |
| `POST` | `/api/scholarships/match` | Scholarship readiness match |
| `POST` | `/api/progress` | Save progress record |
| `GET` | `/api/progress?student_id=` | List student progress |
| `DELETE` | `/api/progress?student_id=` | Clear student progress |

Interactive docs: `/docs` (local) or `https://your-app.vercel.app/docs`

## Environment Variables

Copy `.env.example` to `.env`:

```env
APP_NAME=TUTall Backend
APP_ENV=development
ENABLE_AI=true
ENABLE_COHERE=true
COHERE_API_KEY=
COHERE_MODEL=command-r7b-12-2024
ENABLE_OPENROUTER=true
OPENROUTER_API_KEY=
OPENROUTER_MODEL=mistralai/mistral-7b-instruct:free
ENABLE_GEMINI=false
ENABLE_GROQ=false
DEMO_MODE=false
ALLOWED_ORIGINS=http://localhost:5500,http://127.0.0.1:5500,https://bebecpp.github.io/TUTall_frontend
MAX_TOPIC_LENGTH=120
MAX_TEXT_LENGTH=800
RATE_LIMIT_PER_MINUTE=40
DATABASE_URL=
```

| Variable | Description |
|----------|-------------|
| `ENABLE_AI` | Master AI switch (`false` uses local engine only) |
| `ENABLE_COHERE` | Enable Cohere as primary provider |
| `COHERE_API_KEY` | Cohere API key (server-side only) |
| `COHERE_MODEL` | Cohere model, default `command-r7b-12-2024` |
| `ENABLE_OPENROUTER` | Enable OpenRouter as secondary provider |
| `OPENROUTER_API_KEY` | OpenRouter API key (server-side only) |
| `OPENROUTER_MODEL` | Model name, default `mistralai/mistral-7b-instruct:free` |
| `ENABLE_GEMINI` | Legacy Gemini provider flag (default `false`) |
| `ENABLE_GROQ` | Legacy Groq provider flag (default `false`) |
| `DEMO_MODE` | Force local engine when `true` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |
| `DATABASE_URL` | Supabase Postgres connection string (optional) |

The backend **never crashes** if `OPENROUTER_API_KEY` or `DATABASE_URL` is missing.

## Supabase Postgres Setup

### 1. Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and create a project
2. Wait for the database to finish provisioning

### 2. Run the schema

Open **SQL Editor** in Supabase and run the contents of [`schema.sql`](./schema.sql).

Tables created:

| Table | Purpose |
|-------|---------|
| `students` | Student identifiers from the frontend |
| `learning_progress` | Quiz/topic progress records |
| `scholarship_profiles` | Submitted scholarship readiness profiles |
| `ai_request_logs` | Gemini vs fallback request audit trail |

Alternatively, the backend runs `init_db()` on startup and applies the same schema when `DATABASE_URL` is configured.

### 3. Get the connection string

In Supabase: **Project Settings → Database → Connection string → URI**

Use the **Session pooler** or **Direct connection** URI for serverless:

```text
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

Add it to `.env`:

```env
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

### 4. Storage behavior

- **With `DATABASE_URL`**: progress, scholarship profiles, and AI logs persist in Supabase Postgres
- **Without `DATABASE_URL`**: in-memory fallback keeps demos working locally
- **On database error**: API still returns a normal response; a safe warning is logged server-side

No SQLite is used in production.

## Local Setup

### 1. Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Add GEMINI_API_KEY if you want live AI responses
```

### 4. Run locally

```bash
python -m uvicorn app.main:app --reload
```

Open:

- Health: http://127.0.0.1:8000/health
- Docs: http://127.0.0.1:8000/docs

### 5. Run tests

```bash
pytest -v
```

## Vercel Deployment

### 1. Push to GitHub

Ensure the repository root contains `api/index.py`, `app/`, `requirements.txt`, and `vercel.json`.

### 2. Import to Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import your GitHub repository
3. Framework Preset: **Other**
4. Root Directory: repository root

### 3. Set environment variables

In Vercel Project Settings → Environment Variables, add:

- `ENABLE_AI=true`
- `ENABLE_COHERE=true`
- `COHERE_API_KEY`
- `COHERE_MODEL=command-r7b-12-2024`
- `ENABLE_OPENROUTER=true`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL=mistralai/mistral-7b-instruct:free`
- `ENABLE_GEMINI=false`
- `ENABLE_GROQ=false`
- `DEMO_MODE=false`
- `DATABASE_URL` (Supabase Postgres URI)
- `ALLOWED_ORIGINS` (include your frontend URL)
- `APP_ENV=production`

### 4. Deploy

Vercel routes all traffic to `api/index.py`:

```python
from app.main import app
```

### 5. Verify

```bash
curl https://YOUR-PROJECT.vercel.app/health
```

### Deployment notes

- Vercel entrypoint is `api/index.py`, which imports `app` from `app.main`.
- The legacy `tutall-security-backend/` folder is excluded from serverless bundles.
- Set `DATABASE_URL` to enable Supabase persistence; without it, progress uses in-memory fallback.
- Set `ENABLE_AI=false` or `DEMO_MODE=true` to force the AccessSTEM local engine.

## Frontend Integration

### AI Assistant (chat panel)

```javascript
const response = await fetch(`${API_BASE}/api/accessstem/assistant`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    topic: "Newton's Laws",
    question: "Can you explain this with an example?",
    difficulty: "beginner",
    mode: "learning",
    student_context: "high school student preparing for quiz",
  }),
});
```

### JavaScript (fetch)

```javascript
const API_BASE = "https://YOUR-PROJECT.vercel.app";

async function explainTopic(topic) {
  const response = await fetch(`${API_BASE}/api/accessstem/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      topic,
      difficulty: "beginner",
      low_bandwidth: false,
    }),
  });
  return response.json();
}
```

### Flutter (Dio)

```dart
final dio = Dio(BaseOptions(
  baseUrl: 'https://YOUR-PROJECT.vercel.app',
  headers: {'Content-Type': 'application/json'},
));

Future<Map<String, dynamic>> explainTopic(String topic) async {
  final response = await dio.post('/api/accessstem/explain', data: {
    'topic': topic,
    'difficulty': 'beginner',
    'low_bandwidth': false,
  });
  return response.data;
}
```

Check `source` in AI responses:

- `"cohere"` — live AI response from Cohere (primary)
- `"openrouter"` — live AI response from OpenRouter
- `"gemini"` / `"groq"` — fallback live providers
- `"accessstem_local"` — built-in local engine (all providers failed); includes `debug_reason` and `provider_attempts`

Check provider status:

```bash
curl https://YOUR-PROJECT.vercel.app/api/ai/status
```

## cURL Tests

See [curl-tests.md](./curl-tests.md) for copy-paste commands.

## AI Safety Notes

- Cohere, OpenRouter, Gemini, and Groq API keys are **server-side only**
- Prompt injection phrases are blocked with `400` errors
- Hints never reveal the exact correct answer
- Scholarship advice includes a non-guarantee warning
- Internal errors and stack traces are never exposed
- All errors return safe JSON with `request_id`

## Known Limitations

| Limitation | Notes |
|------------|-------|
| In-memory fallback | Used when `DATABASE_URL` is missing or Postgres is temporarily unavailable |
| In-memory rate limiting | Per-instance on Vercel; use Redis for production scale |
| No authentication | Demo MVP; add JWT/session for production |
| Local engine quality | Useful when OpenRouter is unavailable; configure OpenRouter for best results |

## Future Roadmap

- [x] Postgres / Supabase progress persistence
- [ ] Redis-backed distributed rate limiting
- [ ] User authentication (JWT)
- [ ] Admin analytics dashboard
- [ ] Streaming AI responses
- [ ] Multilingual support (Mongolian + English)
- [ ] Webhook notifications for scholarship deadlines

## License

Built for STEMINATE HACKS 2026 — TUTall / AccessSTEM AI.
