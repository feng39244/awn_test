import gradio as gr
import pandas as pd
import re
import logging
import os
import io
from typing import Dict, List, Optional
from gradio_pdf import PDF
import pypdfium2 as pdfium
from datetime import datetime, timezone
from sqlmodel import Session, create_engine, select
from models import Patient, Gender, Provider, Authorization, ServiceType, AuthorizationStatus
import easyocr
from PIL import Image
import tempfile
import numpy as np
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch

# Load environment variables
load_dotenv()
DB_PASSWORD = os.getenv("DB_PASSWORD", "xxx")
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/userdb")
engine = create_engine(DATABASE_URL)

def create_pdf_from_text(text: str) -> bytes:
    """
    Create a PDF file from text input
    
    :param text: Text content to convert to PDF
    :return: PDF file as bytes
    """
    try:
        # Create a BytesIO buffer to store the PDF
        buffer = io.BytesIO()
        
        # Create the PDF
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Set font and size
        c.setFont("Helvetica", 12)
        
        # Split text into lines that fit the page width
        lines = []
        current_line = []
        words = text.split()
        
        for word in words:
            current_line.append(word)
            line_width = c.stringWidth(' '.join(current_line), "Helvetica", 12)
            if line_width > 7 * inch:  # 7 inches is a safe width for letter size
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Write text to PDF
        y = 750  # Start from top of page
        for line in lines:
            if y < 50:  # If we're near the bottom of the page
                c.showPage()  # Start a new page
                y = 750
                c.setFont("Helvetica", 12)
            
            c.drawString(50, y, line)
            y -= 15  # Move down for next line
        
        # Save the PDF
        c.save()
        
        # Get the PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error creating PDF from text: {str(e)}")
        return None

class MedicalInfoExtractor:
    def __init__(self, 
                 key_patterns: Dict[str, List[str]] = None):
        """
        Initialize extractor with extraction methods
        
        :param key_patterns: Dictionary of key extraction patterns
        """
        # Initialize OCR reader
        self.reader = easyocr.Reader(['en'])  # Initialize with English language
        
        # OneCall PDF patterns
        self.onecall_patterns = {
            'patient_name': [
                r'Name:\s*([^\n]+?)(?:\s*Sex:|$)',  # Match name until Sex: or end of line
                r'Name\s*([^\n]+?)(?:\s*Sex:|$)',   # Match name until Sex: or end of line
            ],
            'patient_dob': [
                r'DOB:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Date\s*of\s*Birth\s*[:]*\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'patient_ssn': [
                r'SSN:\s*(\d{3}-\d{2}-\d{4})',
            ],
            'patient_phone': [
                r'Phone:\s*H:\s*(\(\d{3}\)\s*\d{3}-\d{4})',
            ],
            'patient_address': [
                r'Address 1:\s*([^\n]+?)(?:\s*SSN:|$)\nCity/ST/Zip:\s*([^\n]+)',  # Match address until SSN: or end of line
                r'Address:\s*([^\n]+?)(?:\s*SSN:|$)\nCity/ST/Zip:\s*([^\n]+)',     # Match address until SSN: or end of line
            ],
            'employer': [
                r'Employer:\s*([^\n]+)',
            ],
            'injury_date': [
                r'Injury Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'injury_details': [
                r'Details:\s*([^\n]+)',
            ],
            'physician_name': [
                r'Physician:\s*([^\n]+)',
            ],
            'physician_npi': [
                r'NPI Number:\s*(\d+)',
            ],
            'provider_name': [
                r'Provider:\s*([^\n]+)',
            ],
            'authorized_sessions': [
                r'Total Auth:\s*(\d+)',
                r'Frequency=\d+\s*Duration=\d+\s*Total Auth:\s*(\d+)',
            ],
            'authorization_date': [
                r'Auth Effective Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'rx_expiration_date': [
                r'RX Expiration Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'procedure': [
                r'Procedure:\s*([^\n]+)',
            ]
        }
        
        # Text input patterns
        self.text_patterns = {
            'patient_name': [
                r'Name:\s*([^\n]+)',
                r'Name\s*:\s*([^\n]+)',
            ],
            'patient_dob': [
                r'Date\s*of\s*Birth:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DOB:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'patient_phone': [
                r'Phone\s*\(Primary\):\s*(\(\d{3}\)\s*\d{3}-\d{4})',
                r'Phone\s*\(Mobile\):\s*(\(\d{3}\)\s*\d{3}-\d{4})',
                r'Phone\s*\(Alternate\):\s*(\(\d{3}\)\s*\d{3}-\d{4})',
                r'Phone\s*\(Primary\):\s*(\d{3}-\d{3}-\d{4})',
                r'Phone\s*\(Mobile\):\s*(\d{3}-\d{3}-\d{4})',
                r'Phone\s*\(Alternate\):\s*(\d{3}-\d{3}-\d{4})',
            ],
            'patient_address': [
                r'Address:\s*([^\n]+),\s*([^\n]+)',
                r'Address\s*:\s*([^\n]+),\s*([^\n]+)',
            ],
            'injury_date': [
                r'Date\s*of\s*Injury:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DOI:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'body_part': [
                r'Body\s*Part:\s*([^\n]+)',
                r'Body\s*Part\s*:\s*([^\n]+)',
            ],
            'case_id': [
                r'Case\s*ID:\s*([^\n]+)',
                r'Case\s*ID\s*:\s*([^\n]+)',
            ],
            'authorized_sessions': [
                r'Authorized\s*Visits:\s*(\d+)',
                r'Authorized\s*Visits\s*:\s*(\d+)',
                r'Auth\s*Visits:\s*(\d+)',
            ],
            'provider_name': [
                r'FACILITY:\s*Name:\s*([^\n]+)',
                r'FACILITY\s*:\s*Name:\s*([^\n]+)',
            ],
            'provider_address': [
                r'FACILITY:\s*Name:\s*[^\n]+\s*Address:\s*([^\n]+)',
                r'FACILITY\s*:\s*Name:\s*[^\n]+\s*Address:\s*([^\n]+)',
            ],
            'provider_phone': [
                r'FACILITY:\s*Name:\s*[^\n]+\s*Address:\s*[^\n]+\s*Phone:\s*(\d+)',
                r'FACILITY\s*:\s*Name:\s*[^\n]+\s*Address:\s*[^\n]+\s*Phone:\s*(\d+)',
            ],
            'provider_fax': [
                r'FACILITY:\s*Name:\s*[^\n]+\s*Address:\s*[^\n]+\s*Phone:\s*\d+\s*Fax:\s*(\d+)',
                r'FACILITY\s*:\s*Name:\s*[^\n]+\s*Address:\s*[^\n]+\s*Phone:\s*\d+\s*Fax:\s*(\d+)',
            ],
            'physician_name': [
                r'PHYSICIAN:\s*Name:\s*([^\n]+)',
                r'PHYSICIAN\s*:\s*Name:\s*([^\n]+)',
            ],
            'physician_phone': [
                r'PHYSICIAN:\s*Name:\s*[^\n]+\s*Phone:\s*(\(\d{3}\)\s*\d{3}-\d{4})',
                r'PHYSICIAN\s*:\s*Name:\s*[^\n]+\s*Phone:\s*(\(\d{3}\)\s*\d{3}-\d{4})',
            ],
            'service_type': [
                r'Type\s*of\s*Service:\s*([^\n]+)',
                r'Type\s*of\s*Service\s*:\s*([^\n]+)',
                r'Service\s*Type:\s*([^\n]+)',
            ],
            'jurisdiction_state': [
                r'Jurisdiction\s*State:\s*([^\n]+)',
                r'Jurisdiction\s*State\s*:\s*([^\n]+)',
            ],
            'claim_number': [
                r'Claim\s*Number:\s*([^\n]+)',
                r'Claim\s*Number\s*:\s*([^\n]+)',
            ],
            'surgery_date': [
                r'Date\s*of\s*Surgery:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Date\s*of\s*Surgery\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'initial_evaluation_date': [
                r'Initial\s*Evaluation\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Initial\s*Evaluation\s*Date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'initial_evaluation_time': [
                r'Initial\s*Evaluation\s*Time:\s*([^\n]+)',
                r'Initial\s*Evaluation\s*Time\s*:\s*([^\n]+)',
            ]
        }
        
        # Corvel PDF patterns
        self.corvel_patterns = {
            'patient_name': [
                r'CLAIMANT:\s*([^\n]+)',
                r'Claimant:\s*([^\n]+)',
            ],
            'patient_dob': [
                r'DOB:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'claim_number': [
                r'CLAIM\s*#:\s*([^\n]+)',
                r'Claim\s*#:\s*([^\n]+)',
            ],
            'injury_date': [
                r'DOI:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Date\s*of\s*Injury:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'employer': [
                r'INSURED:\s*([^\n]+)',
                r'Insured:\s*([^\n]+)',
            ],
            'carrier': [
                r'CARRIER/TPA:\s*([^\n]+)',
                r'Carrier/TPA:\s*([^\n]+)',
            ],
            'adjuster': [
                r'ADJUSTER:\s*([^\n]+)',
                r'Adjuster:\s*([^\n]+)',
            ],
            'corvel_number': [
                r'CORVEL\s*#\s*([^\n]+)',
                r'CorVel\s*#\s*([^\n]+)',
            ],
            'determination_date': [
                r'Determination\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'rfa_received_date': [
                r'RFA\s*Received\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'provider_name': [
                r'Provider:\s*([^\n]+)',
                r'PROVIDER:\s*([^\n]+)',
            ],
            'pre_cert_number': [
                r'Pre-Cert\s*#:\s*([^\n]+)',
                r'Pre-Cert\s*Number:\s*([^\n]+)',
            ],
            'network': [
                r'Network:\s*([^\n]+)',
            ],
            'service_type': [
                r'Type\s*of\s*Therapy:\s*([^\n]+)',
                r'Type\s*of\s*Service:\s*([^\n]+)',
            ],
            'body_part': [
                r'Body\s*Part:\s*([^\n]+)',
                r'Part:\s*([^\n]+)',
            ],
            'authorized_sessions': [
                r'Certified\s*Visits:\s*(\d+)',
                r'Authorized\s*Visits:\s*(\d+)',
            ],
            'effective_date': [
                r'Effective\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'termination_date': [
                r'Termination\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'facility': [
                r'Facility:\s*([^\n]+)',
                r'FACILITY:\s*([^\n]+)',
            ],
            'claims_examiner': [
                r'Claims\s*Examiner:\s*([^\n]+)',
                r'Claims\s*Examiner\s*Name:\s*([^\n]+)',
            ],
            'contact_phone': [
                r'Contact\s*Information:\s*(\d{10})',
                r'Phone:\s*(\d{10})',
            ],
            'hours_of_operation': [
                r'Hours\s*of\s*operation:\s*([^\n]+)',
            ]
        }
        
        # HomeLink PDF patterns
        self.homelink_patterns = {
            'patient_name': [
                r'Patient\s*Name:\s*([^\n]+)',
                r'Patient:\s*([^\n]+)',
            ],
            'patient_dob': [
                r'Date\s*of\s*Birth:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DOB:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'patient_phone': [
                r'Phone:\s*(\d{3}-\d{3}-\d{4})',
                r'Alt:\s*Phone:\s*(\d{3}-\d{3}-\d{4})',
            ],
            'patient_address': [
                r'([^\n]+)\n([^\n]+,\s*[A-Z]{2}\s*\d{5})',
            ],
            'injury_date': [
                r'Date\s*of\s*Injury:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DOI:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'diagnosis': [
                r'Diagnosis:\s*([^\n]+)',
            ],
            'physician_name': [
                r'Physician:\s*([^\n]+)',
            ],
            'physician_phone': [
                r'Physician\s*Phone:\s*(\d{3}-\d{3}-\d{4})',
            ],
            'provider_name': [
                r'To:\s*([^\n]+)',
                r'Servicing\s*Location\s*([^\n]+)',
            ],
            'provider_address': [
                r'([^\n]+)\n([^\n]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)',
            ],
            'provider_phone': [
                r'Phone:\s*(\d{3}-\d{3}-\d{4})',
            ],
            'provider_fax': [
                r'Fax:\s*(\d{3}-\d{3}-\d{4})',
            ],
            'service_type': [
                r'Service\s*Type:\s*([^\n]+)',
                r'Therapy/Service:\s*([^\n]+)',
            ],
            'authorized_sessions': [
                r'Total\s*Visits\s*(\d+)',
                r'Auth\'d\s*Visits\s*(\d+)',
            ],
            'authorization_date': [
                r'Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'order_number': [
                r'Order\s*#:\s*([^\n]+)',
                r'HOMELINK\s*Order:\s*([^\n]+)',
            ],
            'contact_name': [
                r'Contact:\s*([^\n]+)',
            ],
            'contact_phone': [
                r'Phone/Fax:\s*(\d{10})',
            ],
            'contact_email': [
                r'Email:\s*([^\n]+)',
            ],
            'height': [
                r'Height:\s*([^\n]+)',
            ],
            'weight': [
                r'Weight:\s*([^\n]+)',
            ],
            'language': [
                r'Language:\s*([^\n]+)',
            ],
            'start_date': [
                r'Start\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'end_date': [
                r'End\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'treatment_description': [
                r'Rental\s*Description\s*([^\n]+)',
            ]
        }
        
        # Update with custom patterns if provided
        self.key_patterns = self.onecall_patterns if key_patterns is None else {**self.onecall_patterns, **key_patterns}

    def get_patterns_for_type(self, pdf_type: str) -> Dict[str, List[str]]:
        """
        Get the appropriate patterns based on PDF type
        
        :param pdf_type: Type of PDF (onecall, corvel, or homelink)
        :return: Dictionary of patterns for the specified PDF type
        """
        if pdf_type and pdf_type.lower() == 'onecall':
            return self.onecall_patterns
        elif pdf_type and pdf_type.lower() == 'corvel':
            return self.corvel_patterns
        elif pdf_type and pdf_type.lower() == 'homelink':
            return self.homelink_patterns
        else:
            return self.text_patterns  # Default to text patterns if no PDF type specified

    def extract_text_from_pdf(self, pdf_path: str, pdf_type: str = None) -> str:
        """
        Extract text from PDF using pypdfium2 and easyocr for Corvel and HomeLink PDFs
        
        :param pdf_path: Path to the PDF file
        :param pdf_type: Type of PDF (onecall, corvel, or homelink)
        :return: Extracted text from the PDF
        """
        try:
            # Open the PDF
            pdf = pdfium.PdfDocument(pdf_path)
            
            # Extract text from all pages
            extracted_text = ""
            for page_index in range(len(pdf)):
                # Render the page to text
                page = pdf[page_index]
                
                # For Corvel and HomeLink PDFs, use easyocr OCR
                if pdf_type and pdf_type.lower() in ['corvel', 'homelink']:
                    # Convert PDF page to image
                    bitmap = page.render(
                        scale=2.0,  # Higher scale for better OCR quality
                        rotation=0
                    )
                    
                    # Convert bitmap to PIL Image
                    image = bitmap.to_pil()
                    
                    # Convert PIL Image to numpy array for easyocr
                    image_np = np.array(image)
                    
                    # Use easyocr to extract text from the image
                    results = self.reader.readtext(image_np)
                    
                    # Combine all detected text
                    page_text = "\n".join([text[1] for text in results])
                    print(f"\n\n\n\n\n\n\n\n\n page text for {pdf_type} PDF:", page_text)
                else:
                    # For other PDFs, use regular text extraction
                    text_page = page.get_textpage()
                    page_text = text_page.get_text_bounded()
                
                # Append page text
                extracted_text += page_text + "\n"
                
                # Debug: Save extracted text to file for analysis
                if pdf_type and pdf_type.lower() in ['corvel', 'homelink']:
                    debug_filename = f'{pdf_type.lower()}_debug.txt'
                    with open(debug_filename, 'w', encoding='utf-8') as f:
                        f.write(extracted_text)
                    print(f"\n=== {pdf_type} PDF Content Saved to {debug_filename} ===")
            
            return extracted_text
        
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""

    def extract_key_information(self, input_source: str, is_pdf: bool = False, pdf_type: str = None) -> Dict[str, Optional[str]]:
        """
        Extract key information from input source (PDF or text)
        
        :param input_source: Path to PDF or raw text
        :param is_pdf: Flag to indicate if input is a PDF file
        :param pdf_type: Type of PDF (onecall, corvel, or homelink)
        :return: Dictionary of extracted information
        """
        # Extract text based on input type
        full_text = self.extract_text_from_pdf(input_source, pdf_type) if is_pdf else input_source
        
        # Debug: Print the full text for analysis
        print("\n=== Full Text for Analysis ===")
        print(full_text)
        print("===============================\n")
        
        # Get appropriate patterns based on PDF type
        patterns = self.get_patterns_for_type(pdf_type) if is_pdf and pdf_type else self.text_patterns
        
        # Debug: Print the patterns being used
        print("\n=== Patterns Being Used ===")
        for key, key_patterns in patterns.items():
            print(f"\n{key}:")
            for pattern in key_patterns:
                print(f"  - {pattern}")
        print("===============================\n")
        
        # Extract information using patterns
        extracted_info = {}
        for key, key_patterns in patterns.items():
            extracted_info[key] = None
            for pattern in key_patterns:
                try:
                    match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    if match:
                        # For address fields that have multiple groups, combine them
                        if key == 'patient_address' and len(match.groups()) > 1:
                            extracted_value = f"{match.group(1)}, {match.group(2)}"
                        else:
                            # Try to get the first capturing group, or the entire match if no groups
                            extracted_value = match.group(1) if match.groups() else match.group(0)
                        extracted_info[key] = extracted_value.strip()
                        print(f"✓ Matched {key} with pattern: {pattern}")
                        print(f"  Value: {extracted_value}")
                        break
                    else:
                        print(f"✗ No match for {key} with pattern: {pattern}")
                except Exception as e:
                    print(f"Error matching {key} with pattern {pattern}: {e}")
        
        # Add PDF type to extracted info
        if is_pdf and pdf_type:
            extracted_info['pdf_type'] = pdf_type
        
        # Additional debugging: print full text if no matches found
        if all(value is None for value in extracted_info.values()):
            print("No matches found. Full text:")
            print(full_text)
        
        return extracted_info

    def save_to_database(self, extracted_info: Dict[str, Optional[str]], pdf_file: Optional[str] = None, text_input: Optional[str] = None) -> str:
        """
        Save extracted information to database with semantic field mapping
        
        :param extracted_info: Dictionary of extracted information
        :param pdf_file: Path to the PDF file if available
        :param text_input: Raw text input if available
        :return: Success/error message
        """
        try:
            with Session(engine) as session:
                # Extract patient information
                patient_name = extracted_info.get('patient_name', '').strip()
                name_parts = patient_name.split()
                first_name = name_parts[0] if name_parts else "Unknown"
                last_name = name_parts[-1] if len(name_parts) > 1 else "Unknown"
                middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else None

                # Map date fields based on PDF type
                pdf_type = extracted_info.get('pdf_type', '').lower()
                dob = None
                if extracted_info.get('patient_dob'):
                    try:
                        dob = datetime.strptime(extracted_info['patient_dob'], '%m/%d/%Y').date()
                    except ValueError:
                        logger.warning(f"Invalid date format: {extracted_info['patient_dob']}")

                # Create patient record with mapped fields
                patient = Patient(
                    first_name=first_name,
                    last_name=last_name,
                    middle_name=middle_name,
                    date_of_birth=dob,
                    gender=Gender.OTHER,  # Default to OTHER since we don't extract gender
                    address=extracted_info.get('patient_address'),
                    phone=extracted_info.get('patient_phone'),
                    client_number=extracted_info.get('case_id'),  # Using case_id as client number
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                session.add(patient)
                session.commit()
                session.refresh(patient)

                # Handle provider record
                provider = None
                if extracted_info.get('provider_name'):
                    # Check if provider already exists
                    existing_provider = session.exec(
                        select(Provider).where(Provider.name == extracted_info['provider_name'])
                    ).first()
                    
                    if existing_provider:
                        # Use existing provider
                        provider = existing_provider
                        logger.info(f"Using existing provider: {provider.name}")
                    else:
                        # Create new provider
                        provider = Provider(
                            name=extracted_info['provider_name'],
                            address=extracted_info.get('provider_address'),
                            phone=extracted_info.get('provider_phone'),
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc)
                        )
                        session.add(provider)
                        session.commit()
                        session.refresh(provider)
                        logger.info(f"Created new provider: {provider.name}")

                # Create authorization record with mapped fields
                if provider and extracted_info.get('case_id'):
                    # Map service type based on PDF type
                    service_type = ServiceType.OTHER  # Default to OTHER
                    service_type_str = extracted_info.get('service_type', '').lower()
                    
                    # Map service type strings to enum values
                    service_type_mapping = {
                        'physical therapy': ServiceType.PHYSICAL_THERAPY,
                        'pt': ServiceType.PHYSICAL_THERAPY,
                        'occupational therapy': ServiceType.OCCUPATIONAL_THERAPY,
                        'ot': ServiceType.OCCUPATIONAL_THERAPY,
                        'speech therapy': ServiceType.SPEECH_THERAPY,
                        'st': ServiceType.SPEECH_THERAPY,
                    }
                    
                    # Try to map the service type
                    for key, value in service_type_mapping.items():
                        if key in service_type_str:
                            service_type = value
                            break

                    # Map initial evaluation date based on PDF type
                    initial_eval_date = None
                    if pdf_type == 'homelink':
                        # For HomeLink, use start_date or authorization_date
                        date_str = extracted_info.get('start_date') or extracted_info.get('authorization_date')
                    elif pdf_type == 'corvel':
                        # For Corvel, use effective_date
                        date_str = extracted_info.get('effective_date')
                    else:
                        # For OneCall and others, use injury_date
                        date_str = extracted_info.get('injury_date')

                    if date_str:
                        try:
                            initial_eval_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                        except ValueError:
                            logger.warning(f"Invalid date format: {date_str}")

                    if not initial_eval_date:
                        initial_eval_date = datetime.now(timezone.utc).date()

                    # Map number of authorized visits based on PDF type
                    num_visits = 1  # Default value
                    if pdf_type == 'homelink':
                        # For HomeLink, use authorized_sessions or total_visits
                        num_visits = int(extracted_info.get('authorized_sessions') or 
                                       extracted_info.get('total_visits') or 1)
                    elif pdf_type == 'corvel':
                        # For Corvel, use certified_visits or authorized_visits
                        num_visits = int(extracted_info.get('certified_visits') or 
                                       extracted_info.get('authorized_visits') or 1)
                    else:
                        # For OneCall and others, use authorized_sessions
                        num_visits = int(extracted_info.get('authorized_sessions') or 1)

                    # Handle authorization form file
                    authorization_form = None
                    if pdf_file:
                        try:
                            # Read the original PDF file as binary data
                            with open(pdf_file, 'rb') as f:
                                authorization_form = f.read()
                            logger.info(f"Successfully read PDF file: {pdf_file}")
                        except Exception as e:
                            logger.error(f"Error reading PDF file: {str(e)}")
                    elif text_input:
                        # Convert text input to PDF
                        authorization_form = create_pdf_from_text(text_input)
                        if not authorization_form:
                            logger.warning("Failed to create PDF from text input")

                    # Create authorization record with mapped fields
                    authorization = Authorization(
                        patient_id=patient.patient_id,
                        provider_id=provider.provider_id,
                        claim_number=extracted_info.get('claim_number', ''),
                        num_authorized_visits=num_visits,
                        service_type=service_type,
                        initial_evaluation_date=initial_eval_date,
                        status=AuthorizationStatus.PENDING,
                        notes=f"Case ID: {extracted_info.get('case_id')}",
                        authorization_form=authorization_form,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    session.add(authorization)
                    session.commit()
                    session.refresh(authorization)

                    return f"Successfully saved patient and authorization information. Patient ID: {patient.patient_id}, Authorization ID: {authorization.authorization_id}"
                else:
                    return f"Successfully saved patient information. Patient ID: {patient.patient_id}"

        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            return f"Error saving to database: {str(e)}"

def create_medical_extractor_app():
    """
    Create Gradio app for medical information extraction
    """
    # Initialize extractor
    extractor = MedicalInfoExtractor()
    
    # Store extracted information and PDF file
    extracted_data = {
        'info': None,
        'pdf_file': None,
        'text_input': None
    }

    def fetch_saved_record(authorization_id: int) -> str:
        """
        Fetch the saved record from the database
        
        :param authorization_id: ID of the saved authorization record
        :return: Formatted string containing the record details
        """
        try:
            with Session(engine) as session:
                # Query the authorization record with related patient and provider
                query = select(Authorization).where(Authorization.authorization_id == authorization_id)
                result = session.exec(query).first()
                
                if result:
                    # Format the record details
                    record_text = "Saved Record Details:\n\n"
                    record_text += f"Authorization ID: {result.authorization_id}\n"
                    record_text += f"Patient: {result.patient.first_name} {result.patient.last_name}\n"
                    record_text += f"Provider: {result.provider.name}\n"
                    record_text += f"Claim Number: {result.claim_number}\n"
                    record_text += f"Service Type: {result.service_type.value}\n"
                    record_text += f"Authorized Visits: {result.num_authorized_visits}\n"
                    record_text += f"Initial Evaluation Date: {result.initial_evaluation_date}\n"
                    record_text += f"Status: {result.status.value}\n"
                    record_text += f"Created At: {result.created_at}\n"
                    return record_text
                else:
                    return "Record not found."
        except Exception as e:
            logger.error(f"Error fetching saved record: {str(e)}")
            return f"Error fetching saved record: {str(e)}"

    def extract_info(pdf_file, text_input, pdf_type):
        """
        Extract information from input and store it
        """
        # Determine input source
        if pdf_file and text_input:
            return "Please use either PDF upload OR text input, not both.", None, None, None
        
        try:
            # PDF file processing
            if pdf_file:
                logger.debug(f"PDF File received: {pdf_file}")
                
                # Verify file exists and is a PDF
                if not os.path.exists(pdf_file):
                    logger.error(f"File does not exist: {pdf_file}")
                    return "File does not exist.", None, None, None
                
                if not pdf_file.lower().endswith('.pdf'):
                    logger.error(f"Not a PDF file: {pdf_file}")
                    return "Please upload a valid PDF file.", None, None, None
                
                # Check if PDF type is selected
                if not pdf_type:
                    logger.error("No PDF type selected")
                    return "Please select a PDF type (OneCall, Corvel, or HomeLink).", None, None, None
                
                # Extract information from PDF
                extracted_info = extractor.extract_key_information(pdf_file, is_pdf=True, pdf_type=pdf_type)
                input_source = pdf_file
                
                # Store the extracted data
                extracted_data['info'] = extracted_info
                extracted_data['pdf_file'] = pdf_file
                extracted_data['text_input'] = None
            
            # Text input processing
            elif text_input:
                logger.debug("Text input received")
                extracted_info = extractor.extract_key_information(text_input, is_pdf=False)
                input_source = "Text Input"
                
                # Store the extracted data
                extracted_data['info'] = extracted_info
                extracted_data['pdf_file'] = None
                extracted_data['text_input'] = text_input
            
            else:
                return "Please upload a PDF or enter text.", None, None, None
            
            # Format results for display
            result_text = "Extracted Information:\n"
            result_text += "\n".join([f"{key.replace('_', ' ').title()}: {value or 'Not Found'}" 
                                       for key, value in extracted_info.items()])
            
            # Create DataFrame for tabular view
            df = pd.DataFrame.from_dict(extracted_info, orient='index', columns=['Value'])
            df.index.name = 'Key'
            df = df.reset_index()
            
            logger.info("Information extraction successful")
            return result_text, df, input_source, None
        
        except Exception as e:
            logger.error(f"Error processing input: {str(e)}")
            return f"Error processing input: {str(e)}", None, None, None

    def save_to_database():
        """
        Save the stored extracted information to database
        """
        if not extracted_data['info']:
            return "No extracted information available. Please extract information first.", None, None, None
        
        try:
            # Save to database using stored information
            save_result = extractor.save_to_database(
                extracted_data['info'],
                extracted_data['pdf_file'],
                extracted_data['text_input']
            )
            
            # Format the result text
            result_text = "Extracted Information:\n"
            result_text += "\n".join([f"{key.replace('_', ' ').title()}: {value or 'Not Found'}" 
                                       for key, value in extracted_data['info'].items()])
            result_text += f"\n\n{save_result}"
            
            # Create DataFrame for tabular view
            df = pd.DataFrame.from_dict(extracted_data['info'], orient='index', columns=['Value'])
            df.index.name = 'Key'
            df = df.reset_index()
            
            # Fetch and display the saved record
            saved_record_text = None
            if "Authorization ID:" in save_result:
                auth_id = int(save_result.split("Authorization ID:")[1].strip())
                saved_record_text = fetch_saved_record(auth_id)
            
            return result_text, df, extracted_data['pdf_file'], saved_record_text
            
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            return f"Error saving to database: {str(e)}", None, None, None

    # Create Gradio interface
    with gr.Blocks(title="Medical Information Extractor") as demo:
        gr.Markdown("# Medical Information Extractor")
        
        with gr.Row():
            with gr.Column(scale=1):
                # Input options
                with gr.Tabs():
                    with gr.TabItem("PDF Upload"):
                        # Add radio buttons for PDF type selection
                        pdf_type = gr.Radio(
                            choices=["OneCall", "Corvel", "HomeLink"],
                            label="Select PDF Type",
                            value=None
                        )
                        pdf_input = gr.File(label="Upload PDF", file_types=['.pdf'])
                    
                    with gr.TabItem("Text Input"):
                        text_input = gr.Textbox(label="Paste Text", lines=10, placeholder="Paste your medical document text here...")
                
                # Extract button
                extract_btn = gr.Button("Extract Information", variant="primary")
                
                # Outputs
                text_output = gr.Textbox(label="Extracted Text", lines=10)
                df_output = gr.DataFrame(label="Extracted Information")
            
            with gr.Column(scale=1):
                # PDF Preview (only visible for PDF uploads)
                pdf_preview = PDF(label="PDF Preview", interactive=True)

        # Save button in a new row to span full width
        with gr.Row():
            save_btn = gr.Button("Save to Database", variant="secondary", scale=1)

        # Saved record display
        saved_record_output = gr.Textbox(label="Saved Record", lines=10, visible=True)

        # Event handlers
        pdf_input.upload(
            fn=lambda file: file, 
            inputs=pdf_input, 
            outputs=pdf_preview
        )
        
        extract_btn.click(
            fn=extract_info,
            inputs=[pdf_input, text_input, pdf_type], 
            outputs=[text_output, df_output, pdf_preview, saved_record_output]
        )
        
        save_btn.click(
            fn=save_to_database,
            inputs=None,
            outputs=[text_output, df_output, pdf_preview, saved_record_output]
        )
        
        # Explanatory text
        gr.Markdown("""
        ### How to Use
        1. Choose between PDF Upload or Text Input
        2. If uploading PDF:
           - Select the PDF type (OneCall, Corvel, or HomeLink)
           - Upload the PDF file
        3. If using text input:
           - Paste the text directly
        4. Click "Extract Information" to view the extracted data
        5. Click "Save to Database" to save the information
        
        #### Notes
        - Supports PDF and direct text input
        - Uses advanced regex for information extraction
        - Cross-platform compatibility
        """)

    return demo

# Launch the app
if __name__ == "__main__":
    demo = create_medical_extractor_app()
    demo.launch(debug=True, share=True)