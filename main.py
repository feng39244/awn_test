from fastapi import FastAPI, Depends, HTTPException, status, Request
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
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import csv
import io
import os
from typing import Optional
# Create FastAPI app
app = FastAPI(title="CMS-1500 Billing System")

# Set up templates directory
templates = Jinja2Templates(directory="templates")
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

# @app.get("/patients/", response_model=List[Patient])
# def read_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     patients = db.exec(select(Patient).offset(skip).limit(limit)).all()
#     return patients

@app.get("/patients/", response_class=HTMLResponse)
async def read_patients(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    patients = db.exec(select(Patient).offset(skip).limit(limit)).all()
    return templates.TemplateResponse(
        "all-patients.html",
        {
            "request": request,
            "patients": patients,
            "skip": skip,
            "limit": limit
        }
    )

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

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Ready to Bill route
@app.get("/ready-to-bill/", response_class=HTMLResponse)
async def read_ready_to_bill(request: Request, db: Session = Depends(get_db)):
    # Placeholder: Filter patients (e.g., IDs < 1000)
    patients = db.exec(select(Patient).where(Patient.patient_id < 1000)).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-bill"}
    )

# Ready to Schedule route
@app.get("/ready-to-schedule/", response_class=HTMLResponse)
async def read_ready_to_schedule(request: Request, db: Session = Depends(get_db)):
    # Placeholder: Filter patients (e.g., IDs between 1000 and 2000)
    patients = db.exec(select(Patient).where(Patient.patient_id.between(1000, 2000))).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-schedule"}
    )

# Ready to Confirm route
@app.get("/ready-to-confirm/", response_class=HTMLResponse)
async def read_ready_to_confirm(request: Request, db: Session = Depends(get_db)):
    # Placeholder: Filter patients (e.g., IDs between 2000 and 3000)
    patients = db.exec(select(Patient).where(Patient.patient_id.between(2000, 3000))).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-confirm"}
    )

# Ready to Report route
@app.get("/ready-to-report/", response_class=HTMLResponse)
async def read_ready_to_report(request: Request, db: Session = Depends(get_db)):
    # Placeholder: Filter patients (e.g., IDs between 3000 and 4000)
    patients = db.exec(select(Patient).where(Patient.patient_id.between(3000, 4000))).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-report"}
    )

# Ready to View route
@app.get("/ready-to-view/", response_class=HTMLResponse)
async def read_ready_to_view(request: Request, db: Session = Depends(get_db)):
    # Placeholder: Filter patients (e.g., IDs > 4000)
    patients = db.exec(select(Patient).where(Patient.patient_id > 4000)).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-view"}
    )
# Sync Google Drive route
@app.get("/sync-drive", response_class=HTMLResponse)
async def sync_drive(request: Request, filter_name: str = "patient"):
    try:
        service = get_drive_service()
        # Query files with name filter
        query = f"'{filter_name}' in name"
        results = service.files().list(
            q=query,
            pageSize=10,
            fields="nextPageToken, files(id, name, mimeType, webViewLink)"
        ).execute()
        files = results.get('files', [])
        return templates.TemplateResponse(
            "drive_files.html",
            {"request": request, "files": files, "filter_name": filter_name}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/upload-appointments")
async def upload_appointments_page(request: Request):
    """Render the appointment upload page"""
    return templates.TemplateResponse("upload_appointments.html", {"request": request})

@app.post("/api/upload-appointments")
async def upload_appointments(
    file: UploadFile = File(...),
    has_headers: bool = Form(True)
):
    """
    Process the uploaded CSV file with patient appointment data
    
    Args:
        file: The uploaded CSV file
        has_headers: Whether the file has headers in the first row
    
    Returns:
        JSON response with success status or error message
    """
    try:
        # Read the CSV file content
        contents = await file.read()
        
        # Decode and parse CSV
        decoded_content = contents.decode('utf-8')
        csv_data = io.StringIO(decoded_content)
        
        # Parse CSV with pandas
        if has_headers:
            df = pd.read_csv(csv_data)
        else:
            df = pd.read_csv(csv_data, header=None)
            # Assign default column names
            default_columns = [
                'patient_id', 'patient_name', 'appointment_date', 
                'appointment_time', 'service_type', 'insurance_provider'
            ]
            # If the number of columns doesn't match, extend or truncate the defaults list
            if len(df.columns) <= len(default_columns):
                df.columns = default_columns[:len(df.columns)]
            else:
                # Add numbered columns for any extras
                extended_columns = default_columns + [f'column_{i}' for i in range(len(default_columns)+1, len(df.columns)+1)]
                df.columns = extended_columns
        
        # TODO: You would typically validate and process the data here
        # For example, check required columns, data types, etc.
        
        # TODO: Save the data to your database
        # For demonstration, we'll just print the first few rows
        print(f"Processed {len(df)} appointment records")
        print(df.head())
        
        # Return success response
        return JSONResponse(
            content={
                "success": True,
                "message": f"Successfully processed {len(df)} appointment records",
                "rows_processed": len(df)
            }
        )
        
    except Exception as e:
        # Return error response
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": str(e)
            }
        )