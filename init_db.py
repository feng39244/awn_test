from sqlmodel import SQLModel, create_engine
from models import (
    Patient, InsuranceCompany, PatientInsurance, Provider,
    DiagnosisCode, ProcedureCode, Claim, ClaimDiagnosis,
    ServiceLine, Location, Appointment, Authorization
)
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/awn_test")

def init_db():
    # Create engine
    engine = create_engine(DATABASE_URL, echo=True)
    
    # Create all tables
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    init_db() 