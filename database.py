from sqlmodel import SQLModel, Session, create_engine, select
from typing import Generator, Optional
from datetime import datetime
from pydantic import EmailStr
from sqlmodel import Field
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_PASSWORD = os.getenv("DB_PASSWORD", "xxx")

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/userdb")
engine = create_engine(DATABASE_URL)

# Define the User model - moved from main.py
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: EmailStr = Field(unique=True, index=True)
    hashed_password: str
    role: str = "user"
    last_login_time: Optional[datetime] = None

class Token(SQLModel):
    access_token: str
    token_type: str

def create_tables():
    """Create all database tables"""
    SQLModel.metadata.create_all(engine)

def get_db() -> Generator[Session, None, None]:
    """Get database session with context management"""
    with Session(engine) as session:
        yield session

def get_user(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.exec(select(User).where(User.email == email)).first()