"""Quick local provider diagnostics (no secrets printed)."""

from app.config import get_settings
from app.providers import PROVIDER_ORDER, run_provider_diagnostics, try_provider_text

get_settings.cache_clear()
settings = get_settings()

print("=== AI Status ===")
print("cohere_enabled:", settings.cohere_enabled)
print("cohere_configured:", settings.cohere_configured)
print("cohere_model:", settings.cohere_model)
print("openrouter_configured:", settings.openrouter_configured)
print("gemini_configured:", settings.gemini_configured)
print("groq_configured:", settings.groq_configured)
print("active_strategy:", settings.active_strategy)
print()

print("=== Provider Test ===")
for name, diag in run_provider_diagnostics().items():
    print(
        f"{name}: enabled={diag['enabled']} "
        f"configured={diag['configured']} ok={diag['ok']} error={diag['error_code']}"
    )
print()

print("=== Chain probe ===")
for provider in PROVIDER_ORDER:
    result = try_provider_text(provider, "Say only: provider works")
    preview = (result.text or "")[:80].replace("\n", " ")
    print(f"{provider}: error={result.error_code} has_text={bool(result.text)} preview={preview!r}")

print()
print("=== Explain endpoint probe ===")
from app.ai_engine import generate_explanation

explain = generate_explanation("Gravity", "beginner", False)
print("source:", explain.get("source"))
print("debug_reason:", explain.get("debug_reason"))
if explain.get("provider_attempts"):
    for attempt in explain["provider_attempts"]:
        print(" attempt:", attempt)
