from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.config import settings

# Import API v1 routers
#from app.api.v1 import user, item
from app.api.v1.hr import job as hr_job
from app.api.v1.applicants import router as applicants  # Applicants router

# from app.api.v2 import ...  # Future API versions

def create_app() -> FastAPI:
    # Initialize logging
    setup_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="FastAPI application structured for scalability",
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
     
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API v1 routers
    # app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
    # app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])
    app.include_router(hr_job.router, prefix="/api/v1/hr/jobs", tags=["HR Jobs"])
    app.include_router(applicants.router, prefix="/api/v1/applicants", tags=["Applicants"])  # NEW

    # Startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        print("Starting up...")
        # e.g., connect to DB, init caches, etc.

    @app.on_event("shutdown")
    async def shutdown_event():
        print("Shutting down...")
        # e.g., close DB connections

    return app

app = create_app()


