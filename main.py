from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from datetime import datetime, timedelta, time
from typing import List, Optional
import pandas as pd
import csv
import io
import os
from sqlalchemy import func, or_

# Import from our separated modules
from database import get_db, create_tables, User, get_user
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from models import (
    Patient, PatientCreate, PatientRead,
    InsuranceCompany, InsuranceCompanyCreate, InsuranceCompanyRead,
    PatientInsurance, PatientInsuranceCreate, PatientInsuranceRead,
    Appointment, AppointmentCreate, AppointmentRead,
    Provider, DiagnosisCode, ProcedureCode, Claim, ServiceLine,
    UserCreate, UserRead, Token, TokenData,
    Gender, AppointmentStatus, ClaimStatus,
    Location, LocationCreate, LocationRead,
    Authorization
)
from seed import insert_sample_data
import appointment_service
from fastapi.templating import Jinja2Templates
from medical_pdf_extractor_ui import MedicalInfoExtractor

extractor = MedicalInfoExtractor()

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

@app.post("/patients/", response_model=PatientRead)
async def create_patient(patient_data: PatientCreate, db: Session = Depends(get_db)):
    try:
        patient = Patient(**patient_data.dict(exclude_unset=True))
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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

@app.get("/patients/{patient_id}", response_model=PatientRead)
def read_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

# Insurance company endpoints
@app.post("/insurance-companies/", response_model=InsuranceCompanyRead)
def create_insurance_company(insurance: InsuranceCompanyCreate, db: Session = Depends(get_db)):
    try:
        db_insurance = InsuranceCompany(**insurance.dict(exclude_unset=True))
        db.add(db_insurance)
        db.commit()
        db.refresh(db_insurance)
        return db_insurance
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/insurance-companies/", response_model=List[InsuranceCompanyRead])
def read_insurance_companies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    insurance_companies = db.exec(select(InsuranceCompany).offset(skip).limit(limit)).all()
    return insurance_companies

# Patient insurance endpoints
@app.post("/patient-insurances/", response_model=PatientInsuranceRead)
def create_patient_insurance(patient_insurance: PatientInsuranceCreate, db: Session = Depends(get_db)):
    try:
        # Validate patient and insurance exist
        patient = db.get(Patient, patient_insurance.patient_id)
        insurance = db.get(InsuranceCompany, patient_insurance.insurance_id)
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        if not insurance:
            raise HTTPException(status_code=404, detail="Insurance company not found")
        
        db_patient_insurance = PatientInsurance(**patient_insurance.dict(exclude_unset=True))
        db.add(db_patient_insurance)
        db.commit()
        db.refresh(db_patient_insurance)
        return db_patient_insurance
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/patient-insurances/by-patient/{patient_id}", response_model=List[PatientInsuranceRead])
def read_patient_insurances(patient_id: int, db: Session = Depends(get_db)):
    insurances = db.exec(select(PatientInsurance).where(PatientInsurance.patient_id == patient_id)).all()
    return insurances

# Authentication endpoints
@app.post("/register", response_model=UserRead)
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

@app.get("/users/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Ready to Bill route
@app.get("/ready-to-bill/", response_class=HTMLResponse)
async def read_ready_to_bill(request: Request, db: Session = Depends(get_db)):
    patients = db.exec(select(Patient).where(Patient.patient_id < 1000)).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-bill"}
    )

# Ready to Schedule route
@app.get("/ready-to-schedule/", response_class=HTMLResponse)
async def read_ready_to_schedule(request: Request, db: Session = Depends(get_db)):
    patients = db.exec(select(Patient).where(Patient.patient_id.between(1000, 2000))).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-schedule"}
    )

# Ready to Confirm route
@app.get("/ready-to-confirm/", response_class=HTMLResponse)
async def read_ready_to_confirm(request: Request, db: Session = Depends(get_db)):
    patients = db.exec(select(Patient).where(Patient.patient_id.between(2000, 3000))).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-confirm"}
    )

# Ready to Report route
@app.get("/ready-to-report/", response_class=HTMLResponse)
async def read_ready_to_report(request: Request, db: Session = Depends(get_db)):
    patients = db.exec(select(Patient).where(Patient.patient_id.between(3000, 4000))).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-report"}
    )

# Ready to View route
@app.get("/ready-to-view/", response_class=HTMLResponse)
async def read_ready_to_view(request: Request, db: Session = Depends(get_db)):
    patients = db.exec(select(Patient).where(Patient.patient_id > 4000)).all()
    return templates.TemplateResponse(
        "patient_list.html",
        {"request": request, "patients": patients, "status_filter": "ready-to-view"}
    )

# Sync Google Drive route
@app.get("/sync-drive", response_class=HTMLResponse)
async def sync_drive(request: Request, filter_name: str = "patient"):
    try:
        from google_drive_service import get_drive_service  # Import here to avoid startup issues
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
    has_headers: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Process the uploaded CSV file with patient appointment data.

    Args:
        file: The uploaded CSV file.
        has_headers: Whether the file has headers in the first row.
        db: Database session.

    Returns:
        JSON response with success status or error message.
    """
    try:
        # Validate file format
        if not file.filename.endswith('.csv'):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid file format. Please upload a CSV file."
                }
            )

        # Call the service function to process the CSV
        stats = appointment_service.process_uploaded_appointments(
            file=file,
            has_headers=has_headers,
            session=db
        )

        # Return success response with stats
        return JSONResponse(
            content={
                "success": True,
                "message": f"Successfully processed {stats['total_processed']} appointment records",
                "stats": stats
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

@app.get("/appointments/", response_class=HTMLResponse)
async def read_appointments(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    appointments = db.exec(select(Appointment).offset(skip).limit(limit)).all()
    print("appointments", appointments)
    return templates.TemplateResponse(
        "all_appointments.html",
        {
            "request": request,
            "appointments": appointments,
            "skip": skip,
            "limit": limit
        }
    )

# Location endpoints
@app.post("/locations/", response_model=LocationRead)
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    try:
        db_location = Location(**location.dict(exclude_unset=True))
        db.add(db_location)
        db.commit()
        db.refresh(db_location)
        return db_location
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/locations/", response_model=List[LocationRead])
def read_locations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    locations = db.exec(select(Location).offset(skip).limit(limit)).all()
    return locations

# Appointment endpoints
@app.post("/appointments/", response_model=AppointmentRead)
def create_appointment(appointment: AppointmentCreate, db: Session = Depends(get_db)):
    try:
        # Validate related entities exist
        patient = db.get(Patient, appointment.patient_id)
        provider = db.get(Provider, appointment.provider_id)
        location = db.get(Location, appointment.location_id)
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        
        db_appointment = Appointment(**appointment.dict(exclude_unset=True))
        db.add(db_appointment)
        db.commit()
        db.refresh(db_appointment)
        return db_appointment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/appointments/{appointment_id}", response_model=AppointmentRead)
def read_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment

@app.delete("/appointments/{appointment_id}", response_model=dict)
def delete_appointment_endpoint(appointment_id: int, session: Session = Depends(get_db)):
    """
    Delete an appointment by ID.
    
    Args:
        appointment_id: ID of the appointment to delete
        session: Database session
        
    Returns:
        dict: Success/failure message
    """
    success = delete_appointment(session, appointment_id)
    if success:
        return {"message": "Appointment deleted successfully"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Appointment not found or could not be deleted"
    )

@app.get("/authorizations", response_class=HTMLResponse)
async def list_authorizations(request: Request, session: Session = Depends(get_db)):
    """List all authorizations."""
    authorizations = session.query(Authorization).all()
    return templates.TemplateResponse(
        "all_authorization.html",
        {"request": request, "authorizations": authorizations}
    )

@app.delete("/authorizations/{authorization_id}", response_model=dict)
def delete_authorization_endpoint(authorization_id: int, session: Session = Depends(get_db)):
    """
    Delete an authorization by ID.
    
    Args:
        authorization_id: ID of the authorization to delete
        session: Database session
        
    Returns:
        dict: Success/failure message
    """
    success = delete_authorization(session, authorization_id)
    if success:
        return {"message": "Authorization deleted successfully"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Authorization not found or could not be deleted"
    )
@app.route("/extract-medical-info", methods=["GET", "POST"])
async def extract_medical_info(request: Request, 
                                file: UploadFile = File(None), 
                                text_input: str = Form(None)):
    """
    Extract medical information and render Jinja2 template
    """
    extracted_info = None
    error = None

    try:
        # Check if it's a POST request with file or text input
        if request.method == "POST":
            # Validate input
            if file is None and not text_input:
                error = "Please provide either a PDF file or text input"
            
            # PDF file processing
            elif file:
                # Check file type
                if not file.filename.lower().endswith('.pdf'):
                    error = "Only PDF files are supported"
                else:
                    # Read file bytes
                    pdf_bytes = await file.read()
                    
                    # Extract information from PDF
                    extracted_info = extractor.extract_key_information(pdf_bytes, is_pdf=True)
            
            # Text input processing
            elif text_input:
                # Extract information from text
                extracted_info = extractor.extract_key_information(text_input, is_pdf=False)
        
        # Render template with extracted information
        return templates.TemplateResponse("medical_extractor.html", {
            "request": request,
            "extracted_info": extracted_info,
            "error": error
        })
    
    except Exception as e:
        # Handle any unexpected errors
        error = str(e)
        return templates.TemplateResponse("medical_extractor.html", {
            "request": request,
            "error": error
        })