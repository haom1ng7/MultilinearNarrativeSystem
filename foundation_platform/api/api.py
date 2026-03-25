import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from foundation_platform.api.services.db_service import init_db, load_registry

from foundation_platform.api.routes import assets, export, health, ws, narrative, generation

app = FastAPI(title="Foundation Platform API v42.0 [Modality Router & Persistence]")

@app.on_event("startup")
async def startup_event():
    init_db()
    # Phase 42: Restore asset_registry from SQLite
    from foundation_platform.api.state import asset_registry
    restored = load_registry()
    asset_registry.update(restored)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
ASSETS_DIR_FP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR_FP, exist_ok=True)
# Serve both possible locations for generated assets
app.mount("/static/assets", StaticFiles(directory=ASSETS_DIR_FP), name="static_assets")

app.include_router(health.router)
app.include_router(ws.router)
app.include_router(narrative.router)
app.include_router(assets.router)
app.include_router(generation.router)
app.include_router(export.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8095)
