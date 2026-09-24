from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.core.settings import get_settings
from app.services.pipeline import ClaimsPipeline
from app.storage.repository import ClaimsRepository


def create_app() -> FastAPI:
    app = FastAPI(title="Plum Claims Pipeline", version="0.1.0")
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.eval_dir.mkdir(parents=True, exist_ok=True)
    app.state.settings = settings
    app.state.repository = ClaimsRepository(settings.db_path)
    app.state.pipeline = ClaimsPipeline(app.state.repository)
    app.include_router(api_router)

    assets_dir = settings.frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False, response_model=None)
    async def root():
        index_path = settings.frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return HTMLResponse(
            "<html><body><h1>Plum Claims Pipeline</h1><p>Build the frontend in <code>frontend/</code> to serve the UI here.</p></body></html>"
        )

    @app.get("/{path_name:path}", include_in_schema=False, response_model=None)
    async def spa_fallback(path_name: str):
        if path_name.startswith("api/"):
            return HTMLResponse("Not Found", status_code=404)
        index_path = settings.frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return HTMLResponse(
            "<html><body><h1>Plum Claims Pipeline</h1><p>Frontend not built yet.</p></body></html>"
        )

    return app


app = create_app()
