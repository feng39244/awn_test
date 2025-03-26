from sqlmodel import SQLModel, create_engine
from models import Appointment
import os
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/userdb")

def fix_appointments_table():
    # Create engine
    engine = create_engine(DATABASE_URL, echo=True)
    
    # Drop the existing appointments table
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS public.appointments CASCADE"))
        conn.commit()
    
    # Create the appointments table with the correct schema
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    fix_appointments_table() 