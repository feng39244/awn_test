from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, ForwardRef
from datetime import date, datetime, time
from pydantic import EmailStr, validator
from typing import Optional

# Define the schema models, separated from database models
class UserCreate(SQLModel):
    email: EmailStr
    password: str
    role: str = "user"



class TimeStampMixin:
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

class Patient(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "patients"
    
    patient_id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str = Field(...)
    middle_name: Optional[str] = None
    last_name: str
    date_of_birth: date
    gender: str
    address: str
    city: str
    state: str
    zipcode: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    client_number: Optional[str] = None
    
    # Relationships
    insurances: List["PatientInsurance"] = Relationship(back_populates="patient")
    claims: List["Claim"] = Relationship(back_populates="patient")
    appointments: List["Appointment"] = Relationship(back_populates="patient")
    
    def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if self.created_at is None:
                self.created_at = datetime.now()
            if self.updated_at is None:
                self.updated_at = datetime.now()

class InsuranceCompany(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "insurance_companies"
    
    insurance_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: str
    city: str
    state: str
    zipcode: str
    phone: Optional[str] = None
    payer_id: Optional[str] = None
    
    # Relationships
    patient_insurances: List["PatientInsurance"] = Relationship(back_populates="insurance")


class PatientInsurance(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "patient_insurance"
    
    patient_insurance_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")
    insurance_id: int = Field(foreign_key="insurance_companies.insurance_id")
    policy_number: str
    group_number: Optional[str] = None
    relationship_to_insured: str
    insured_first_name: Optional[str] = None
    insured_middle_name: Optional[str] = None
    insured_last_name: Optional[str] = None
    insured_dob: Optional[date] = None
    insured_gender: Optional[str] = None
    insured_address: Optional[str] = None
    insured_city: Optional[str] = None
    insured_state: Optional[str] = None
    insured_zipcode: Optional[str] = None
    insured_phone: Optional[str] = None
    is_primary: bool = True
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="insurances")
    insurance: "InsuranceCompany" = Relationship(back_populates="patient_insurances")
    claims: List["Claim"] = Relationship(back_populates="patient_insurance")


class Provider(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "providers"
    
    provider_id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    credentials: Optional[str] = None
    npi: str = Field(unique=True)
    ein: Optional[str] = None
    address: str
    city: str
    state: str
    zipcode: str
    phone: Optional[str] = None
    taxonomy_code: Optional[str] = None
    
    # Relationships
    claims: List["Claim"] = Relationship(back_populates="provider")
    service_lines: List["ServiceLine"] = Relationship(
        back_populates="rendering_provider",
        sa_relationship_kwargs={"foreign_keys": "ServiceLine.rendering_provider_id"}
    )
    appointments: List["Appointment"] = Relationship(back_populates="practitioner")


class DiagnosisCode(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "diagnosis_codes"
    
    diagnosis_id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True)
    description: str
    
    # Relationships
    claim_diagnoses: List["ClaimDiagnosis"] = Relationship(back_populates="diagnosis")


class ProcedureCode(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "procedure_codes"
    
    procedure_id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True)
    description: str
    type: str  # CPT or HCPCS
    
    # Relationships
    service_lines: List["ServiceLine"] = Relationship(back_populates="procedure")


class Claim(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "claims"
    
    claim_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")
    provider_id: int = Field(foreign_key="providers.provider_id")
    patient_insurance_id: int = Field(foreign_key="patient_insurance.patient_insurance_id")
    claim_number: Optional[str] = Field(unique=True, default=None)
    date_of_service_from: date
    date_of_service_to: date
    place_of_service: Optional[str] = None
    prior_authorization_number: Optional[str] = None
    referring_provider_npi: Optional[str] = None
    total_charge: float
    status: str = "PENDING"
    
    # Relationships
    patient: Patient = Relationship(back_populates="claims")
    provider: Provider = Relationship(back_populates="claims")
    patient_insurance: PatientInsurance = Relationship(back_populates="claims")
    diagnoses: List["ClaimDiagnosis"] = Relationship(back_populates="claim")
    service_lines: List["ServiceLine"] = Relationship(back_populates="claim")


class ClaimDiagnosis(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "claim_diagnosis"
    
    claim_diagnosis_id: Optional[int] = Field(default=None, primary_key=True)
    claim_id: int = Field(foreign_key="claims.claim_id")
    diagnosis_id: int = Field(foreign_key="diagnosis_codes.diagnosis_id")
    diagnosis_pointer: int  # 1-12 for position on form
    
    # Relationships
    claim: Claim = Relationship(back_populates="diagnoses")
    diagnosis: DiagnosisCode = Relationship(back_populates="claim_diagnoses")


class ServiceLine(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "service_lines"
    
    service_line_id: Optional[int] = Field(default=None, primary_key=True)
    claim_id: int = Field(foreign_key="claims.claim_id")
    date_from: date
    date_to: date
    place_of_service: Optional[str] = None
    procedure_id: int = Field(foreign_key="procedure_codes.procedure_id")
    modifier_1: Optional[str] = None
    modifier_2: Optional[str] = None
    modifier_3: Optional[str] = None
    modifier_4: Optional[str] = None
    diagnosis_pointers: str  # comma-separated integers (e.g., "1,2,3")
    charges: float
    units: int = 1
    rendering_provider_id: Optional[int] = Field(default=None, foreign_key="providers.provider_id")
    epsdt_family_plan: Optional[str] = None
    emergency: bool = False
    
    # Relationships
    claim: Claim = Relationship(back_populates="service_lines")
    procedure: ProcedureCode = Relationship(back_populates="service_lines")
    rendering_provider: Optional[Provider] = Relationship(
        back_populates="service_lines",
        sa_relationship_kwargs={"foreign_keys": "ServiceLine.rendering_provider_id"}
    )


class Location(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "locations"
    
    location_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    phone: Optional[str] = None
    
    # Relationships
    appointments: List["Appointment"] = Relationship(back_populates="location")


class Appointment(SQLModel, TimeStampMixin, table=True):
    __tablename__ = "appointments"
    
    appointment_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")
    practitioner_id: int = Field(foreign_key="providers.provider_id")
    location_id: int = Field(foreign_key="locations.location_id")
    
    # Appointment time details
    appointment_datetime: datetime
    end_time: time
    
    # Appointment metadata
    appointment_type: str
    appointment_subtype: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    flag: Optional[str] = None
    status: str = "Pending"
    
    # Other fields
    client_type: Optional[str] = None
    sex: Optional[str] = None
    gender_identity: Optional[str] = None
    
    # Relationships
    patient: Patient = Relationship(back_populates="appointments")
    practitioner: Provider = Relationship(back_populates="appointments")
    location: Location = Relationship(back_populates="appointments")  # Fixed here
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


# Schemas for API requests/responses
class PatientCreate(SQLModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    date_of_birth: date
    gender: str
    address: str
    city: str
    state: str
    zipcode: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    client_number: Optional[str] = None


class InsuranceCompanyCreate(SQLModel):
    name: str
    address: str
    city: str
    state: str
    zipcode: str
    phone: Optional[str] = None
    payer_id: Optional[str] = None


class PatientInsuranceCreate(SQLModel):
    patient_id: int
    insurance_id: int
    policy_number: str
    group_number: Optional[str] = None
    relationship_to_insured: str
    insured_first_name: Optional[str] = None
    insured_middle_name: Optional[str] = None
    insured_last_name: Optional[str] = None
    insured_dob: Optional[date] = None
    insured_gender: Optional[str] = None
    insured_address: Optional[str] = None
    insured_city: Optional[str] = None
    insured_state: Optional[str] = None
    insured_zipcode: Optional[str] = None
    insured_phone: Optional[str] = None
    is_primary: bool = True


class LocationCreate(SQLModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    phone: Optional[str] = None


class AppointmentCreate(SQLModel):
    patient_id: int
    practitioner_id: int
    location_id: int
    appointment_datetime: datetime
    end_time: time
    appointment_type: str
    appointment_subtype: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    flag: Optional[str] = None
    status: str = "Pending"
    client_type: Optional[str] = None
    sex: Optional[str] = None
    gender_identity: Optional[str] = None