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

def get_or_create_patient(session, client_name, client_number, mobile, sex, gender_identity, postcode, state):
    patient = session.query(Patient).filter(Patient.client_number == client_number).first()
    if patient:
        print(f"Found patient with patient_id={patient.patient_id}")
        return patient
    patient = Patient(
        first_name=client_name.split()[0] if client_name else "Unknown",
        last_name=client_name.split()[-1] if client_name and len(client_name.split()) > 1 else None,
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
    session.flush()
    print(f"Created patient with patient_id={patient.patient_id}")
    return patient

def get_or_create_provider(session, name):
    try:
        print(f"Searching for provider with name: {name}")
        print(f"Session: {session}")
        print(f"Provider class: {Provider}")
        query = session.query(Provider)
        print(f"Query object: {query}")
        provider = query.filter(Provider.name == name).first()  # Breakpoint here
        if provider:
            print(f"Found existing provider: {provider.name}, ID: {provider.provider_id}")
            return provider
        print(f"No existing provider found for name: {name}")
        provider = Provider(name=name, created_at=datetime.now(), updated_at=datetime.now())
        session.add(provider)
        session.flush()
        print(f"Created new provider: {provider.name}, ID: {provider.provider_id}")
        return provider
    except AttributeError as ae:
        print(f"Attribute Error occurred: {str(ae)}")
        print("Possible issues: session or Provider class might not be properly defined")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

def get_or_create_location(session, location_name):
    try:
        print(f"Searching for location with name: {location_name}")
        print(f"Session: {session}")
        print(f"Location class: {Location}")
        query = session.query(Location)
        print(f"Query object: {query}")
        location = query.filter(Location.name == location_name).first()
        if location:
            print(f"Found existing location: {location.name}, ID: {location.location_id}")
            return location
        print(f"No existing location found for name: {location_name}")
        location = Location(name=location_name, created_at=datetime.now(), updated_at=datetime.now())
        session.add(location)
        session.flush()
        print(f"Created new location: {location.name}, ID: {location.location_id}")
        return location
    except AttributeError as ae:
        print(f"Attribute Error occurred: {str(ae)}")
        print("Possible issues: session or Location class might not be properly defined")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

def parse_datetime(date_str: str) -> datetime:
    """Parse a date string into a datetime object.

    Args:
        date_str: The date string to parse (e.g., "31/12/2023", "2023-12-31 14:30:00").

    Returns:
        A datetime object. Returns datetime.now() if parsing fails.
    """
    if not date_str:
        print(f"parse_datetime: Empty date string, using default: {datetime.now()}")
        return datetime.now()

    # Try different date and date-time formats
    formats = [
        "%m/%d/%Y %I:%M %p",  # 3/08/2025 11:00 AM (your CSV format)
        "%d/%m/%Y",           # 31/12/2023
        "%Y-%m-%d",           # 2023-12-31
        "%d-%m-%Y",           # 31-12-2023
        "%m/%d/%Y",           # 12/31/2023
        "%d %b %Y",           # 31 Dec 2023
        "%d %B %Y",           # 31 December 2023
        "%d/%m/%Y %H:%M:%S",  # 31/12/2023 14:30:00
        "%Y-%m-%d %H:%M:%S",  # 2023-12-31 14:30:00
        "%d-%m-%Y %H:%M:%S",  # 31-12-2023 14:30:00
        "%m/%d/%Y %H:%M:%S",  # 12/31/2023 14:30:00
        "%d %b %Y %H:%M:%S",  # 31 Dec 2023 14:30:00
        "%d %B %Y %H:%M:%S",  # 31 December 2023 14:30:00
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue  # Try the next format

    print(f"parse_datetime: Failed to parse date '{date_str}', using default: {datetime.now()}")
    return datetime.now()


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
            
            dt = datetime.strptime(fmt, "%H:%M:%S")  # Adjust format as needed
            return dt.time()
        except ValueError:
            continue
    
    return None


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