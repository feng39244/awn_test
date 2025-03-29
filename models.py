from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, ForwardRef
from datetime import date, datetime, time, timezone
from pydantic import EmailStr, validator, constr
from typing import Optional
from decimal import Decimal
from enum import Enum
import re

# Validation functions
def validate_phone(phone: Optional[str]) -> Optional[str]:
    if phone is None:
        return None
    # Remove any non-digit characters
    phone_digits = re.sub(r'\D', '', phone)
    if len(phone_digits) != 10:
        raise ValueError("Phone number must be 10 digits")
    return f"{phone_digits[:3]}-{phone_digits[3:6]}-{phone_digits[6:]}"

def validate_zipcode(zipcode: Optional[str]) -> Optional[str]:
    if zipcode is None:
        return None
    if not re.match(r'^\d{5}(-\d{4})?$', zipcode):
        raise ValueError("Invalid zipcode format. Must be 5 digits or 5+4 digits")
    return zipcode

def validate_npi(npi: Optional[str]) -> Optional[str]:
    if npi is None:
        return None
    if not re.match(r'^\d{10}$', npi):
        raise ValueError("NPI must be 10 digits")
    return npi

def validate_state(state: Optional[str]) -> Optional[str]:
    if state is None:
        return None
    valid_states = {'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 
                   'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 
                   'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 
                   'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 
                   'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'}
    state_upper = state.upper()
    if state_upper not in valid_states:
        raise ValueError("Invalid state code")
    return state_upper

# Enums for various status and type fields
class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

class AppointmentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"

class ClaimStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    DENIED = "denied"
    PAID = "paid"
    APPEALED = "appealed"

class ProcedureType(str, Enum):
    CPT = "CPT"
    HCPCS = "HCPCS"

class InsuranceRelationship(str, Enum):
    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"
    OTHER = "other"

class AuthorizationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"

class ServiceType(str, Enum):
    PHYSICAL_THERAPY = "physical_therapy"
    OCCUPATIONAL_THERAPY = "occupational_therapy"
    SPEECH_THERAPY = "speech_therapy"
    OTHER = "other"

# Schema Models for API requests
class UserBase(SQLModel):
    email: EmailStr
    role: str = Field(default="user", regex="^(user|admin|provider)$")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserRead(UserBase):
    id: int

class Token(SQLModel):
    access_token: str
    token_type: str

class TokenData(SQLModel):
    email: Optional[str] = None

class PatientBase(SQLModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    middle_name: Optional[str] = Field(default=None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    address: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=2)
    zipcode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    client_number: Optional[str] = Field(default=None, max_length=50)

    # Validators
    _validate_phone = validator('phone', allow_reuse=True)(validate_phone)
    _validate_zipcode = validator('zipcode', allow_reuse=True)(validate_zipcode)
    _validate_state = validator('state', allow_reuse=True)(validate_state)

class PatientCreate(PatientBase):
    pass

class PatientRead(PatientBase):
    patient_id: int
    created_at: datetime
    updated_at: datetime

class InsuranceCompanyBase(SQLModel):
    name: str = Field(..., max_length=200)
    address: str = Field(..., max_length=200)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=2)
    zipcode: str
    phone: Optional[str] = None
    payer_id: Optional[str] = Field(default=None, max_length=50)

    # Validators
    _validate_phone = validator('phone', allow_reuse=True)(validate_phone)
    _validate_zipcode = validator('zipcode', allow_reuse=True)(validate_zipcode)
    _validate_state = validator('state', allow_reuse=True)(validate_state)

class InsuranceCompanyCreate(InsuranceCompanyBase):
    pass

class InsuranceCompanyRead(InsuranceCompanyBase):
    insurance_id: int
    created_at: datetime
    updated_at: datetime

class PatientInsuranceBase(SQLModel):
    patient_id: int
    insurance_id: int
    policy_number: str = Field(..., max_length=50)
    group_number: Optional[str] = Field(default=None, max_length=50)
    relationship_to_insured: InsuranceRelationship
    insured_first_name: Optional[str] = Field(default=None, max_length=100)
    insured_middle_name: Optional[str] = Field(default=None, max_length=100)
    insured_last_name: Optional[str] = Field(default=None, max_length=100)
    insured_dob: Optional[date] = None
    insured_gender: Optional[Gender] = None
    insured_address: Optional[str] = Field(default=None, max_length=200)
    insured_city: Optional[str] = Field(default=None, max_length=100)
    insured_state: Optional[str] = Field(default=None, max_length=2)
    insured_zipcode: Optional[str] = None
    insured_phone: Optional[str] = None
    is_primary: bool = True

    # Validators
    _validate_phone = validator('insured_phone', allow_reuse=True)(validate_phone)
    _validate_zipcode = validator('insured_zipcode', allow_reuse=True)(validate_zipcode)
    _validate_state = validator('insured_state', allow_reuse=True)(validate_state)

class PatientInsuranceCreate(PatientInsuranceBase):
    pass

class PatientInsuranceRead(PatientInsuranceBase):
    patient_insurance_id: int
    created_at: datetime
    updated_at: datetime

class AppointmentBase(SQLModel):
    patient_id: int
    provider_id: int
    location_id: int
    appointment_datetime: datetime
    end_time: Optional[time] = None
    appointment_type: str = Field(default="Unknown", max_length=50)
    appointment_subtype: Optional[str] = Field(default=None, max_length=50)
    invoice_number: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=1000)
    flag: Optional[str] = Field(default=None, max_length=50)
    status: AppointmentStatus = Field(default=AppointmentStatus.PENDING)
    client_type: Optional[str] = Field(default=None, max_length=50)
    sex: Optional[Gender] = None
    gender_identity: Optional[str] = Field(default=None, max_length=50)

    @validator('end_time')
    def validate_end_time(cls, v, values):
        if v is not None and 'appointment_datetime' in values:
            appointment_time = values['appointment_datetime'].time()
            if v <= appointment_time:
                raise ValueError('end_time must be after appointment_datetime')
        return v

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentRead(AppointmentBase):
    appointment_id: int
    created_at: datetime
    updated_at: datetime

# Base mixin for timestamps
class TimeStampMixin:
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

# Define the schema models, separated from database models
class Patient(SQLModel, table=True):
    __tablename__ = "patients"
    
    patient_id: Optional[int] = Field(default=None, primary_key=True)  # Optional, auto-incremented
    first_name: str = Field(..., max_length=100)  # Required
    middle_name: Optional[str] = Field(default=None, max_length=100)  # Optional
    last_name: str = Field(..., max_length=100)  # Required
    date_of_birth: Optional[date] = None  # Optional
    gender: Optional[Gender] = None  # Optional
    address: Optional[str] = Field(default=None, max_length=200)  # Optional
    city: Optional[str] = Field(default=None, max_length=100)  # Optional
    state: Optional[str] = Field(default=None, max_length=2)  # Optional
    zipcode: Optional[str] = None  # Optional
    phone: Optional[str] = None  # Optional
    email: Optional[EmailStr] = None  # Optional
    client_number: Optional[str] = Field(default=None, max_length=50, index=True)  # Optional
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    insurances: List["PatientInsurance"] = Relationship(back_populates="patient")
    claims: List["Claim"] = Relationship(back_populates="patient")
    appointments: List["Appointment"] = Relationship(back_populates="patient")
    authorizations: List["Authorization"] = Relationship(back_populates="patient")

    # Validators
    _validate_phone = validator('phone', allow_reuse=True)(validate_phone)
    _validate_zipcode = validator('zipcode', allow_reuse=True)(validate_zipcode)
    _validate_state = validator('state', allow_reuse=True)(validate_state)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class InsuranceCompany(SQLModel, table=True):
    __tablename__ = "insurance_companies"
    
    insurance_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=200)  # Required
    address: str = Field(..., max_length=200)  # Required
    city: str = Field(..., max_length=100)  # Required
    state: str = Field(..., max_length=2)  # Required
    zipcode: str  # Required
    phone: Optional[str] = None  # Optional
    payer_id: Optional[str] = Field(default=None, max_length=50, index=True)  # Optional
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient_insurances: List["PatientInsurance"] = Relationship(back_populates="insurance")

    # Validators
    _validate_phone = validator('phone', allow_reuse=True)(validate_phone)
    _validate_zipcode = validator('zipcode', allow_reuse=True)(validate_zipcode)
    _validate_state = validator('state', allow_reuse=True)(validate_state)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class PatientInsurance(SQLModel, table=True):
    __tablename__ = "patient_insurance"
    
    patient_insurance_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")  # Required
    insurance_id: int = Field(foreign_key="insurance_companies.insurance_id")  # Required
    policy_number: str = Field(..., max_length=50)  # Required
    group_number: Optional[str] = Field(default=None, max_length=50)  # Optional
    relationship_to_insured: InsuranceRelationship  # Required
    insured_first_name: Optional[str] = Field(default=None, max_length=100)  # Optional
    insured_middle_name: Optional[str] = Field(default=None, max_length=100)  # Optional
    insured_last_name: Optional[str] = Field(default=None, max_length=100)  # Optional
    insured_dob: Optional[date] = None  # Optional
    insured_gender: Optional[Gender] = None  # Optional
    insured_address: Optional[str] = Field(default=None, max_length=200)  # Optional
    insured_city: Optional[str] = Field(default=None, max_length=100)  # Optional
    insured_state: Optional[str] = Field(default=None, max_length=2)  # Optional
    insured_zipcode: Optional[str] = None  # Optional
    insured_phone: Optional[str] = None  # Optional
    is_primary: bool = True  # Required
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="insurances")
    insurance: "InsuranceCompany" = Relationship(back_populates="patient_insurances")
    claims: List["Claim"] = Relationship(back_populates="patient_insurance")

    # Validators
    _validate_phone = validator('insured_phone', allow_reuse=True)(validate_phone)
    _validate_zipcode = validator('insured_zipcode', allow_reuse=True)(validate_zipcode)
    _validate_state = validator('insured_state', allow_reuse=True)(validate_state)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class Provider(SQLModel, table=True):
    __tablename__ = "providers"
    
    provider_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=200, unique=True)  # Required field with unique constraint
    first_name: Optional[str] = Field(default=None, max_length=100)  # Optional
    last_name: Optional[str] = Field(default=None, max_length=100)  # Optional
    middle_name: Optional[str] = Field(default=None, max_length=100)  # Optional
    credentials: Optional[str] = Field(default=None, max_length=50)  # Optional
    npi: Optional[str] = Field(default=None, max_length=10, index=True)  # Optional
    ein: Optional[str] = Field(default=None, max_length=10)  # Optional
    address: Optional[str] = Field(default=None, max_length=200)  # Optional
    city: Optional[str] = Field(default=None, max_length=100)  # Optional
    state: Optional[str] = Field(default=None, max_length=2)  # Optional
    zipcode: Optional[str] = None  # Optional
    phone: Optional[str] = None  # Optional
    taxonomy_code: Optional[str] = Field(default=None, max_length=10)  # Optional
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    claims: List["Claim"] = Relationship(back_populates="provider")
    service_lines: List["ServiceLine"] = Relationship(
        back_populates="rendering_provider",
        sa_relationship_kwargs={"foreign_keys": "ServiceLine.rendering_provider_id"}
    )
    provider_appointments: List["Appointment"] = Relationship(back_populates="provider")
    authorizations: List["Authorization"] = Relationship(back_populates="provider")

    # Validators
    _validate_phone = validator('phone', allow_reuse=True)(validate_phone)
    _validate_zipcode = validator('zipcode', allow_reuse=True)(validate_zipcode)
    _validate_state = validator('state', allow_reuse=True)(validate_state)
    _validate_npi = validator('npi', allow_reuse=True)(validate_npi)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class DiagnosisCode(SQLModel, table=True):
    __tablename__ = "diagnosis_codes"
    
    diagnosis_id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(..., max_length=10, unique=True)  # Required
    description: str = Field(..., max_length=500)  # Required
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    claim_diagnoses: List["ClaimDiagnosis"] = Relationship(back_populates="diagnosis")

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class ProcedureCode(SQLModel, table=True):
    __tablename__ = "procedure_codes"
    
    procedure_id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(..., max_length=10, unique=True)  # Required
    description: str = Field(..., max_length=500)  # Required
    type: ProcedureType  # Required
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    service_lines: List["ServiceLine"] = Relationship(back_populates="procedure")

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class Claim(SQLModel, table=True):
    __tablename__ = "claims"
    
    claim_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")  # Required
    provider_id: int = Field(foreign_key="providers.provider_id")  # Required
    patient_insurance_id: int = Field(foreign_key="patient_insurance.patient_insurance_id")  # Required
    claim_number: Optional[str] = Field(unique=True, default=None, max_length=50, index=True)  # Optional
    date_of_service_from: date  # Required
    date_of_service_to: date  # Required
    place_of_service: Optional[str] = Field(default=None, max_length=2)  # Optional
    prior_authorization_number: Optional[str] = Field(default=None, max_length=50)  # Optional
    referring_provider_npi: Optional[str] = None  # Optional
    total_charge: Decimal = Field(max_digits=10, decimal_places=2)  # Required
    status: ClaimStatus = Field(default=ClaimStatus.PENDING)  # Required
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: Patient = Relationship(back_populates="claims")
    provider: Provider = Relationship(back_populates="claims")
    patient_insurance: PatientInsurance = Relationship(back_populates="claims")
    diagnoses: List["ClaimDiagnosis"] = Relationship(back_populates="claim")
    service_lines: List["ServiceLine"] = Relationship(back_populates="claim")

    # Validators
    @validator('date_of_service_to')
    def validate_service_dates(cls, v, values):
        if 'date_of_service_from' in values and v < values['date_of_service_from']:
            raise ValueError('date_of_service_to must be after or equal to date_of_service_from')
        return v

    _validate_npi = validator('referring_provider_npi', allow_reuse=True)(validate_npi)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class ClaimDiagnosis(SQLModel, table=True):
    __tablename__ = "claim_diagnosis"
    
    claim_diagnosis_id: Optional[int] = Field(default=None, primary_key=True)
    claim_id: int = Field(foreign_key="claims.claim_id")  # Required
    diagnosis_id: int = Field(foreign_key="diagnosis_codes.diagnosis_id")  # Required
    diagnosis_pointer: int = Field(ge=1, le=12)  # 1-12 for position on form
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    claim: Claim = Relationship(back_populates="diagnoses")
    diagnosis: DiagnosisCode = Relationship(back_populates="claim_diagnoses")

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class ServiceLine(SQLModel, table=True):
    __tablename__ = "service_lines"
    
    service_line_id: Optional[int] = Field(default=None, primary_key=True)
    claim_id: int = Field(foreign_key="claims.claim_id")  # Required
    date_from: date  # Required
    date_to: date  # Required
    place_of_service: Optional[str] = Field(default=None, max_length=2)  # Optional
    procedure_id: int = Field(foreign_key="procedure_codes.procedure_id")  # Required
    modifier_1: Optional[str] = Field(default=None, max_length=2)  # Optional
    modifier_2: Optional[str] = Field(default=None, max_length=2)  # Optional
    modifier_3: Optional[str] = Field(default=None, max_length=2)  # Optional
    modifier_4: Optional[str] = Field(default=None, max_length=2)  # Optional
    diagnosis_pointers: str = Field(...)  # Store as JSON string
    charges: Decimal = Field(max_digits=10, decimal_places=2)  # Required
    units: int = Field(ge=1)  # Required
    rendering_provider_id: Optional[int] = Field(default=None, foreign_key="providers.provider_id")  # Optional
    epsdt_family_plan: Optional[str] = Field(default=None, max_length=1)  # Optional
    emergency: bool = False  # Required
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    claim: Claim = Relationship(back_populates="service_lines")
    procedure: ProcedureCode = Relationship(back_populates="service_lines")
    rendering_provider: Optional[Provider] = Relationship(
        back_populates="service_lines",
        sa_relationship_kwargs={"foreign_keys": "ServiceLine.rendering_provider_id"}
    )

    # Validators
    @validator('date_to')
    def validate_service_dates(cls, v, values):
        if 'date_from' in values and v < values['date_from']:
            raise ValueError('date_to must be after or equal to date_from')
        return v

    @validator('diagnosis_pointers')
    def validate_diagnosis_pointers(cls, v):
        try:
            # If it's already a string, try to parse it
            if isinstance(v, str):
                import json
                pointers = json.loads(v)
            else:
                pointers = v
                
            if not isinstance(pointers, list):
                raise ValueError('diagnosis_pointers must be a list')
                
            if not all(1 <= x <= 12 for x in pointers):
                raise ValueError('All diagnosis pointers must be between 1 and 12')
                
            # If it was a list, convert to JSON string
            if not isinstance(v, str):
                import json
                return json.dumps(pointers)
                
            return v
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON format for diagnosis_pointers')
        except Exception as e:
            raise ValueError(f'Invalid diagnosis_pointers: {str(e)}')

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class LocationBase(SQLModel):
    name: str = Field(..., max_length=200)
    address: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=2)
    zipcode: Optional[str] = None
    phone: Optional[str] = None

    # Validators
    _validate_phone = validator('phone', allow_reuse=True)(validate_phone)
    _validate_zipcode = validator('zipcode', allow_reuse=True)(validate_zipcode)
    _validate_state = validator('state', allow_reuse=True)(validate_state)

class LocationCreate(LocationBase):
    pass

class LocationRead(LocationBase):
    location_id: int
    created_at: datetime
    updated_at: datetime

class Location(SQLModel, table=True):
    __tablename__ = "locations"
    
    location_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=200)  # Required
    address: Optional[str] = Field(default=None, max_length=200)  # Optional
    city: Optional[str] = Field(default=None, max_length=100)  # Optional
    state: Optional[str] = Field(default=None, max_length=2)  # Optional
    zipcode: Optional[str] = None  # Optional
    phone: Optional[str] = None  # Optional
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    appointments: List["Appointment"] = Relationship(back_populates="location")

    # Validators
    _validate_phone = validator('phone', allow_reuse=True)(validate_phone)
    _validate_zipcode = validator('zipcode', allow_reuse=True)(validate_zipcode)
    _validate_state = validator('state', allow_reuse=True)(validate_state)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"
    
    appointment_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")  # Required
    provider_id: int = Field(foreign_key="providers.provider_id")  # Required
    location_id: int = Field(foreign_key="locations.location_id")  # Required
    
    appointment_datetime: datetime  # Required
    end_time: Optional[time] = None  # Made optional
    
    appointment_type: str = Field(default="Unknown", max_length=50)  # Added default
    appointment_subtype: Optional[str] = Field(default=None, max_length=50)  # Optional
    invoice_number: Optional[str] = Field(default=None, max_length=50, index=True)  # Optional
    notes: Optional[str] = Field(default=None, max_length=1000)  # Optional
    flag: Optional[str] = Field(default=None, max_length=50)  # Optional
    status: AppointmentStatus = Field(default=AppointmentStatus.PENDING)  # Required
    
    client_type: Optional[str] = Field(default=None, max_length=50)  # Optional
    sex: Optional[Gender] = None  # Optional
    gender_identity: Optional[str] = Field(default=None, max_length=50)  # Optional
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    patient: Patient = Relationship(back_populates="appointments")
    provider: Provider = Relationship(back_populates="provider_appointments")
    location: Location = Relationship(back_populates="appointments")

    # Validators
    @validator('end_time')
    def validate_end_time(cls, v, values):
        if v is not None and 'appointment_datetime' in values:
            appointment_time = values['appointment_datetime'].time()
            if v <= appointment_time:
                raise ValueError('end_time must be after appointment_datetime')
        return v

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()

class AuthorizationBase(SQLModel):
    patient_id: int
    provider_id: int
    claim_number: str = Field(..., max_length=50)
    num_authorized_visits: int = Field(..., ge=1)
    service_type: ServiceType
    initial_evaluation_date: date
    status: AuthorizationStatus = Field(default=AuthorizationStatus.PENDING)
    notes: Optional[str] = Field(default=None, max_length=1000)

class AuthorizationCreate(AuthorizationBase):
    pass

class AuthorizationRead(AuthorizationBase):
    authorization_id: int
    created_at: datetime
    updated_at: datetime

class Authorization(SQLModel, table=True):
    """Authorization record for medical services"""
    __tablename__ = "authorizations"

    authorization_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")
    provider_id: int = Field(foreign_key="providers.provider_id")
    claim_number: Optional[str] = Field(default=None, nullable=True)  # Made optional
    num_authorized_visits: int
    service_type: ServiceType
    initial_evaluation_date: date
    status: AuthorizationStatus
    notes: Optional[str] = Field(default=None)
    authorization_form: Optional[bytes] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    patient: Patient = Relationship(back_populates="authorizations")
    provider: Provider = Relationship(back_populates="authorizations")

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)