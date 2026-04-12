from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.capabilities import router as capabilities_router
from app.api.routes.documents import router as documents_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.settings import router as settings_router
from app.api.routes.skills import router as skills_router
from app.core.config import settings
from app.db import models  # noqa: F401
from app.db.database import Base, engine
from app.web import router as web_router

app = FastAPI(title=settings.app_name, version=settings.app_version)

if settings.use_database_persistence:
    Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/health")
def healthcheck():
    return {
        "status": "ok",
        "service": settings.app_name,
        "async_pipeline": settings.use_async_pipeline,
        "database_persistence": settings.use_database_persistence,
    }


app.include_router(web_router)
app.include_router(jobs_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(evidence_router, prefix="/api")
app.include_router(capabilities_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
