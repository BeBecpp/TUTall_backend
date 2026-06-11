"""Compatibility shim for `from app.main import app` without Vercel auto-entrypoint detection."""


def __getattr__(name: str):
    if name == "app":
        from app.application import app as fastapi_app

        return fastapi_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
