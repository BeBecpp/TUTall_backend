"""Legacy Vercel entrypoint — re-exports the FastAPI app from app.main."""

from app.main import app

__all__ = ["app"]
