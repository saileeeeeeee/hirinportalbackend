from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    emp_id: int # Added emp_id field with constraints
    username: constr(min_length=3, max_length=50)
    password_hash: constr(min_length=6, max_length=255)
    email: EmailStr
    role: constr(pattern="^(HR|Manager|Management)$")  # ✅ changed 'regex' → 'pattern'
    full_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    status: constr(pattern="^(active|inactive)$") = "active"
    last_login: Optional[datetime] = None

    # ✅ new Pydantic v2 config
    model_config = {"from_attributes": True}



