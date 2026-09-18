from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.routes import router


app = FastAPI(
    title=settings.APP_NAME,
    description="AI Meeting Copilot",
    version=settings.APP_VERSION
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://frontend-7tcb410tu-kalyana-sundars-projects.vercel.app",
        "https://frontend-rose-nu-31.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


app.include_router(router)


@app.get("/")
def root():
    return {
        "application": settings.APP_NAME,
        "status": "running",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": settings.APP_NAME
    }