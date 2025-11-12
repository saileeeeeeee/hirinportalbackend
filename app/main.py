# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.config import settings

# === IMPORT ROUTERS ===
from app.api.v1.users.router import router as users_router
from app.api.v1.hr.job import router as hr_job_router
from app.api.v1.applicants.router import router as applicants_router


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="UBTI Hiring Portal - Scalable FastAPI Backend",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(hr_job_router, prefix="/api/v1/hr/jobs", tags=["HR Jobs"])
    app.include_router(applicants_router, prefix="/api/v1/applicants", tags=["Applicants"])

    # Test route
    @app.get("/test-cors")
    def test_cors():
        return {
            "message": "CORS is working!",
            "allowed_origins": settings.get_cors_origins(),
        }

    # Events
    @app.on_event("startup")
    async def startup_event():
        print("Starting up UBTI Hiring Portal...")
        print(f"Project: {settings.PROJECT_NAME}")
        print(f"CORS Allowed Origins: {settings.get_cors_origins()}")

    @app.on_event("shutdown")
    async def shutdown_event():
        print("Shutting down...")

    return app


# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
# CRITICAL: This must be at module level!
app = create_app()
# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←