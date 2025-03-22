from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import or_
from typing import List, Dict, Any
import csv
import io
from datetime import datetime, time
import re
import asyncio
import sys
import os
from sqlmodel import SQLModel, Session, create_engine
from models import Patient, Provider, Location, Appointment, SQLModel
from dotenv import load_dotenv
import os

router = APIRouter(prefix="/import", tags=["import"])

# Database setup for standalone testing
load_dotenv()
DB_PASSWORD = os.getenv("DB_PASSWORD", "xxx")

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/userdb")
engine = create_engine(DATABASE_URL)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency to get session
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db():
    async with engine.connect() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.commit()

# Add a sync engine just for initialization
sync_engine = create_engine(DATABASE_URL)

def init_db_sync():
    SQLModel.metadata.create_all(sync_engine)

def get_or_create_patient(
    session,
    client_name,
    client_number,
    mobile,
    sex,
    gender_identity,
    postcode,
    state
):
    """Get or create a patient record."""
    # Parse first and last name from client_name
    name_parts = client_name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    
    # Check if patient exists by client number
    if client_number:
        existing_patient = session.exec(
            select(Patient).where(Patient.client_number == client_number)
        ).first()
        
        if existing_patient:
            return existing_patient
    
    # Create new patient
    patient = Patient(
        first_name=first_name,
        last_name=last_name,
        client_number=client_number,
        mobile=mobile,
        sex=sex,
        gender_identity=gender_identity,
        postcode=postcode,
        state=state,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    session.add(patient)
    session.flush()  # Get the ID without committing
    
    return patient

def get_or_create_provider(
    session,
    practitioner_code
):
    """Get or create a provider record."""
    # Check if provider exists
    existing_provider = session.exec(
        select(Provider).where(Provider.provider_code == practitioner_code)
    ).first()
    
    if existing_provider:
        return existing_provider
    
    # Create new provider
    provider = Provider(
        provider_code=practitioner_code,
        first_name="Unknown",  # Placeholder
        last_name="Provider",  # Placeholder
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    session.add(provider)
    session.flush()  # Get the ID without committing
    
    return provider

def get_or_create_location(
    session,
    location_name
):
    """Get or create a location record."""
    # Check if location exists
    existing_location = session.exec(
        select(Location).where(Location.name == location_name)
    ).first()
    
    if existing_location:
        return existing_location
    
    # Create new location
    location = Location(
        name=location_name,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    session.add(location)
    session.flush()  # Get the ID without committing
    
    return location

def parse_datetime(date_str):
    """Parse date string into datetime object."""
    if not date_str:
        return None
    
    # Try different date formats
    formats = [
        "%d/%m/%Y",  # 31/12/2023
        "%Y-%m-%d",  # 2023-12-31
        "%d-%m-%Y",  # 31-12-2023
        "%m/%d/%Y",  # 12/31/2023
        "%d %b %Y",  # 31 Dec 2023
        "%d %B %Y",  # 31 December 2023
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None

def parse_time(time_str):
    """Parse time string into datetime.time object."""
    if not time_str:
        return None
    
    # Try different time formats
    formats = [
        "%H:%M",      # 13:30
        "%I:%M %p",   # 1:30 PM
        "%H.%M",      # 13.30
        "%I.%M %p"    # 1.30 PM
    ]
    
    for fmt in formats:
        try:
            time_obj = datetime.strptime(time_str.strip(), fmt).time()
            return time_obj
        except ValueError:
            continue
    
    return None

@router.post("/appointments/csv", status_code=status.HTTP_201_CREATED)
def import_appointments_from_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
        """Import appointments from CSV file."""
        if not file.filename.endswith('.csv'):
            raise ValueError("Invalid file format. Please upload a CSV file.")
        
        contents = file.read()
        buffer = io.StringIO(contents.decode('utf-8-sig'))  # Handle potential BOM
        reader = csv.DictReader(buffer)
        
        # Track stats
        stats = {
            "total_processed": 0,
            "created": 0,
            "errors": 0,
            "error_details": []
        }
        
        for row in reader:
            try:
                stats["total_processed"] += 1
                
                # Get or create patient
                patient = get_or_create_patient(
                    session=session,
                    client_name=row.get("Client", ""),
                    client_number=row.get("Client Number", ""),
                    mobile=row.get("Mobile", ""),
                    sex=row.get("Sex", ""),
                    gender_identity=row.get("Gender Identity", ""),
                    postcode=row.get("Postcode", ""),
                    state=row.get("State", "")
                )
                
                # Get or create provider
                provider = get_or_create_provider(
                    session=session,
                    practitioner_code=row.get("Practitioner", "")
                )
                
                # Get or create location
                location = get_or_create_location(
                    session=session,
                    name=row.get("Location", "")
                )
                
                # Parse appointment date and time
                appointment_datetime = parse_datetime(row.get("Date", ""))
                end_time = parse_time(row.get("End Time", ""))
                
                # Create appointment
                appointment = Appointment(
                    patient_id=patient.patient_id,
                    practitioner_id=provider.provider_id,
                    location_id=location.location_id,
                    appointment_datetime=appointment_datetime,
                    end_time=end_time,
                    appointment_type=row.get("Appointment Type", ""),
                    appointment_subtype=row.get("Type", ""),  # Using the "Type" field for subtype
                    invoice_number=row.get("Invoice", ""),
                    notes=row.get("Appointment Notes", ""),
                    flag=row.get("Appointment Flag", ""),
                    status=row.get("Status", "Pending"),
                    client_type=row.get("Type", ""),
                    sex=row.get("Sex", ""),
                    gender_identity=row.get("Gender Identity", ""),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                session.add(appointment)
                stats["created"] += 1
                
            except Exception as e:
                stats["errors"] += 1
                stats["error_details"].append({
                    "row": stats["total_processed"],
                    "error": str(e)
                })
        
        # Commit all changes at the end
        session.commit()
        
        return stats

def process_csv_file(file_path: str):
    """Process a CSV file using the import function."""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return
    
    print(f"Processing file: {file_path}")
    
    # Use the existing database setup
    from database import get_db, create_tables
    
    # Initialize the database tables
    create_tables()
    
    # Create a mock file object
    class CSVFile:
        def __init__(self, file_path):
            self.file_path = file_path
            self.filename = os.path.basename(file_path)
        
        def read(self):
            with open(self.file_path, 'rb') as f:
                return f.read()
    
    csv_file = CSVFile(file_path)
    
    # Get a database session
    db_gen = get_db()
    session = next(db_gen)
    
    try:
        # Import the data
        result = import_appointments_from_csv(csv_file, session)
        
        # Print results
        print("\nImport Results:")
        print(f"Total processed: {result['total_processed']}")
        print(f"Successfully created: {result['created']}")
        print(f"Errors: {result['errors']}")
        
        if result['errors'] > 0 and result.get('error_details'):
            print("\nError Details:")
            for error in result['error_details']:
                print(f"Row {error['row']}: {error['error']}")
        
        # Query and print some stats
        patients = session.exec(select(Patient)).all()
        providers = session.exec(select(Provider)).all()
        locations = session.exec(select(Location)).all()
        appointments = session.exec(select(Appointment)).all()
        
        print("\nDatabase Statistics:")
        print(f"Patients: {len(patients)}")
        print(f"Providers: {len(providers)}")
        print(f"Locations: {len(locations)}")
        print(f"Appointments: {len(appointments)}")
        
        if len(appointments) > 0:
            print("\nSample Appointment:")
            appt = appointments[0]
            patient = session.get(Patient, appt.patient_id)
            provider = session.get(Provider, appt.practitioner_id)
            location = session.get(Location, appt.location_id)
            
            print(f"Patient: {patient.first_name} {patient.last_name}")
            print(f"Provider: {provider.first_name} {provider.last_name}")
            print(f"Location: {location.name}")
            print(f"Date/Time: {appt.appointment_datetime}")
            print(f"Status: {appt.status}")
    
    finally:
        # Close the session
        session.close()
def main():
    """Main function to run the import process."""
    if len(sys.argv) < 2:
        print("Usage: python import_appointments.py <csv_file_path>")
        return
    
    csv_file_path = sys.argv[1]
    process_csv_file(csv_file_path)

if __name__ == "__main__":
    # Run the asyncio event loop
    main()