from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException  # Add this import to fix the error
from app.config import settings

# # Build the connection string
# DATABASE_URL = (
#     f"mssql+pyodbc://{settings.DB_USER}:{settings.DB_PASSWORD}"
#     f"@{settings.DB_SERVER}:{settings.DB_PORT}/{settings.DB_NAME}"
#     "?driver=ODBC+Driver+17+for+SQL+Server"
# )

DATABASE_URL = (
    "mssql+pyodbc://portaladminuser:UBTI%402025acp@saileedevdb.cb2y0uaqu31r.us-east-2.rds.amazonaws.com:1433/ubtihiringportal?driver=ODBC+Driver+17+for+SQL+Server"
)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=True, fast_executemany=True)

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for FastAPI
def get_db():
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        # Handle any database connection error and raise an HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}"
        )
    finally:
        db.close() 