from sqlalchemy import text
from fastapi import HTTPException
from app.db.connection import SessionLocal  # Import SessionLocal from the connection file
import bcrypt

def create_user(db: Session, user_data: dict):
    try:
        # Check if the username already exists
        existing_user = db.execute(text("SELECT 1 FROM users WHERE username = :username"), {"username": user_data["username"]}).fetchone()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Check if the email already exists
        existing_email = db.execute(text("SELECT 1 FROM users WHERE email = :email"), {"email": user_data["email"]}).fetchone()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")

        # Check if emp_id already exists
        existing_emp_id = db.execute(text("SELECT 1 FROM users WHERE emp_id = :emp_id"), {"emp_id": user_data["emp_id"]}).fetchone()
        if existing_emp_id:
            raise HTTPException(status_code=400, detail="Employee ID already exists")

        # Hash the password before saving
        hashed_password = bcrypt.hashpw(user_data["password_hash"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Raw SQL query to insert the new user
        query = """
        INSERT INTO users (emp_id, username, password_hash, email, role, full_name, department, designation, status)
        VALUES (:emp_id, :username, :password_hash, :email, :role, :full_name, :department, :designation, :status)
        """

        # Execute the query
        db.execute(text(query), {
            "emp_id": user_data["emp_id"],  # Now we are using the emp_id passed in the request
            "username": user_data["username"],
            "password_hash": hashed_password,
            "email": user_data["email"],
            "role": user_data["role"],
            "full_name": user_data.get("full_name"),
            "department": user_data.get("department"),
            "designation": user_data.get("designation"),
            "status": user_data["status"]
        })

        # Commit the transaction
        db.commit()

        return {"message": "User created successfully", "emp_id": user_data["emp_id"]}  # Return emp_id from the request

    except Exception as e:
        db.rollback()  # Rollback transaction in case of error
        raise HTTPException(status_code=400, detail=f"Error creating user: {str(e)}")
