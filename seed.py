from datetime import date, datetime
from sqlmodel import Session
from database import engine
from models import (
    Patient, InsuranceCompany, PatientInsurance, Provider,
    DiagnosisCode, ProcedureCode, Claim, ClaimDiagnosis, ServiceLine
)
from sqlmodel import Session, SQLModel, select
def insert_sample_data():
    """Insert sample data into all tables"""
    with Session(engine) as session:
        # Insert sample patient
        patient = Patient(
            first_name="John",
            middle_name="A",
            last_name="Doe",
            date_of_birth=date(1980, 1, 15),
            gender="M",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zipcode="12345",
            phone="555-123-4567",
            email="john.doe@example.com"
        )
        session.add(patient)
        
        # Insert sample insurance company
        insurance = InsuranceCompany(
            name="Example Health Insurance",
            address="456 Insurance Blvd",
            city="Coverage City",
            state="NY",
            zipcode="67890",
            phone="800-123-4567",
            payer_id="EHI001"
        )
        session.add(insurance)
        
        # Commit to get IDs
        session.commit()
        
        # Insert patient insurance
        patient_insurance = PatientInsurance(
            patient_id=patient.patient_id,
            insurance_id=insurance.insurance_id,
            policy_number="POL123456",
            group_number="GRP987654",
            relationship_to_insured="SELF",
            is_primary=True
        )
        session.add(patient_insurance)
        
        # Insert sample provider
        provider = Provider(
            first_name="Sarah",
            last_name="Smith",
            credentials="MD",
            npi="1234567890",
            ein="12-3456789",
            address="789 Medical Dr",
            city="Doctorville",
            state="CA",
            zipcode="54321",
            phone="555-987-6543",
            taxonomy_code="207Q00000X"
        )
        session.add(provider)
        
        # Insert sample diagnosis codes
        diagnosis1 = DiagnosisCode(
            code="J30.1",
            description="Allergic rhinitis due to pollen"
        )
        diagnosis2 = DiagnosisCode(
            code="R51",
            description="Headache"
        )
        session.add(diagnosis1)
        session.add(diagnosis2)
        
        # Insert sample procedure codes
        procedure1 = ProcedureCode(
            code="99213",
            description="Office visit, established patient, moderate complexity",
            type="CPT"
        )
        procedure2 = ProcedureCode(
            code="85025",
            description="Complete CBC with auto diff WBC",
            type="CPT"
        )
        session.add(procedure1)
        session.add(procedure2)
        
        # Commit to get IDs
        session.commit()
        
        # Insert sample claim
        claim = Claim(
            patient_id=patient.patient_id,
            provider_id=provider.provider_id,
            patient_insurance_id=patient_insurance.patient_insurance_id,
            claim_number="CLM20230001",
            date_of_service_from=date(2023, 1, 15),
            date_of_service_to=date(2023, 1, 15),
            place_of_service="11",  # Office
            total_charge=125.00,
            status="PENDING"
        )
        session.add(claim)
        session.commit()
        
        # Link diagnoses to claim
        claim_diagnosis1 = ClaimDiagnosis(
            claim_id=claim.claim_id,
            diagnosis_id=diagnosis1.diagnosis_id,
            diagnosis_pointer=1
        )
        claim_diagnosis2 = ClaimDiagnosis(
            claim_id=claim.claim_id,
            diagnosis_id=diagnosis2.diagnosis_id,
            diagnosis_pointer=2
        )
        session.add(claim_diagnosis1)
        session.add(claim_diagnosis2)
        
        # Create service lines
        service_line1 = ServiceLine(
            claim_id=claim.claim_id,
            date_from=date(2023, 1, 15),
            date_to=date(2023, 1, 15),
            place_of_service="11",
            procedure_id=procedure1.procedure_id,
            diagnosis_pointers="1,2",
            charges=85.00,
            units=1,
            rendering_provider_id=provider.provider_id
        )
        service_line2 = ServiceLine(
            claim_id=claim.claim_id,
            date_from=date(2023, 1, 15),
            date_to=date(2023, 1, 15),
            place_of_service="11",
            procedure_id=procedure2.procedure_id,
            diagnosis_pointers="1",
            charges=40.00,
            units=1,
            rendering_provider_id=provider.provider_id
        )
        session.add(service_line1)
        session.add(service_line2)
        
        # Final commit
        session.commit()
        
if __name__ == "__main__":
    # Create tables if they don't exist
    SQLModel.metadata.create_all(engine)
    # Insert sample data
    insert_sample_data()
    print("Sample Data inserted!")
    with Session(engine) as session:
        patients = session.exec(select(Patient)).all()
        for patient in patients:
            print(patient.first_name, patient.last_name)