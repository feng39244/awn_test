from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from typing import List
from datetime import datetime, timedelta

# Import from our separated modules
from database import get_db, create_tables, User, Token, get_user
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from models import (
    Patient, PatientCreate,
    InsuranceCompany, InsuranceCompanyCreate,
    PatientInsurance, PatientInsuranceCreate,
    Provider, DiagnosisCode, ProcedureCode, Claim, ServiceLine, 
    UserCreate
)
from seed import insert_sample_data

# Create FastAPI app
app = FastAPI(title="CMS-1500 Billing System")

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Startup event to create tables
@app.on_event("startup")
async def on_startup():
    create_tables()
    # Uncomment to insert sample data on startup
    # insert_sample_data()

# Route to manually trigger sample data insertion
@app.post("/seed-data/")
def seed_sample_data():
    insert_sample_data()
    return {"message": "Sample data inserted successfully"}

# Patient endpoints
@app.post("/patients/", response_model=Patient)
def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    db_patient = Patient.from_orm(patient)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.get("/patients/", response_model=List[Patient])
def read_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    patients = db.exec(select(Patient).offset(skip).limit(limit)).all()
    return patients

@app.get("/patients/{patient_id}", response_model=Patient)
def read_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

# Insurance company endpoints
@app.post("/insurance-companies/", response_model=InsuranceCompany)
def create_insurance_company(insurance: InsuranceCompanyCreate, db: Session = Depends(get_db)):
    db_insurance = InsuranceCompany.from_orm(insurance)
    db.add(db_insurance)
    db.commit()
    db.refresh(db_insurance)
    return db_insurance

@app.get("/insurance-companies/", response_model=List[InsuranceCompany])
def read_insurance_companies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    insurance_companies = db.exec(select(InsuranceCompany).offset(skip).limit(limit)).all()
    return insurance_companies

# Patient insurance endpoints
@app.post("/patient-insurances/", response_model=PatientInsurance)
def create_patient_insurance(patient_insurance: PatientInsuranceCreate, db: Session = Depends(get_db)):
    # Validate patient and insurance exist
    patient = db.get(Patient, patient_insurance.patient_id)
    insurance = db.get(InsuranceCompany, patient_insurance.insurance_id)
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not insurance:
        raise HTTPException(status_code=404, detail="Insurance company not found")
    
    db_patient_insurance = PatientInsurance.from_orm(patient_insurance)
    db.add(db_patient_insurance)
    db.commit()
    db.refresh(db_patient_insurance)
    return db_patient_insurance

@app.get("/patient-insurances/by-patient/{patient_id}", response_model=List[PatientInsurance])
def read_patient_insurances(patient_id: int, db: Session = Depends(get_db)):
    insurances = db.exec(select(PatientInsurance).where(PatientInsurance.patient_id == patient_id)).all()
    return insurances

# Authentication endpoints
@app.post("/register", response_model=User)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Update last login time
    user.last_login_time = datetime.utcnow()
    db.add(user)
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/welcome")
async def read_welcome(current_user: User = Depends(get_current_user)):
    return {"message": f"Welcome {current_user.email}! Role: {current_user.role}"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Serve static index.html at root
@app.get("/")
async def root():
    return FileResponse("static/index.html")