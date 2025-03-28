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

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:92883@localhost:5432/userdb")
engine = create_engine(DATABASE_URL)

class MedicalInfoExtractor:
    def __init__(self, 
                 key_patterns: Dict[str, List[str]] = None):
        """
        Initialize extractor with extraction methods
        
        :param key_patterns: Dictionary of key extraction patterns
        """
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
        
        # Corvel PDF patterns (to be filled with actual patterns)
        self.corvel_patterns = {
            'patient_name': [
                # Add Corvel-specific patterns here
            ],
            'patient_dob': [
                # Add Corvel-specific patterns here
            ],
            'patient_ssn': [
                # Add Corvel-specific patterns here
            ],
            'patient_phone': [
                # Add Corvel-specific patterns here
            ],
            'patient_address': [
                # Add Corvel-specific patterns here
            ],
            'employer': [
                # Add Corvel-specific patterns here
            ],
            'injury_date': [
                # Add Corvel-specific patterns here
            ],
            'injury_details': [
                # Add Corvel-specific patterns here
            ],
            'physician_name': [
                # Add Corvel-specific patterns here
            ],
            'physician_npi': [
                # Add Corvel-specific patterns here
            ],
            'provider_name': [
                # Add Corvel-specific patterns here
            ],
            'authorized_sessions': [
                # Add Corvel-specific patterns here
            ],
            'authorization_date': [
                # Add Corvel-specific patterns here
            ],
            'rx_expiration_date': [
                # Add Corvel-specific patterns here
            ],
            'procedure': [
                # Add Corvel-specific patterns here
            ]
        }
        
        # HomeLink PDF patterns (to be filled with actual patterns)
        self.homelink_patterns = {
            'patient_name': [
                # Add HomeLink-specific patterns here
            ],
            'patient_dob': [
                # Add HomeLink-specific patterns here
            ],
            'patient_ssn': [
                # Add HomeLink-specific patterns here
            ],
            'patient_phone': [
                # Add HomeLink-specific patterns here
            ],
            'patient_address': [
                # Add HomeLink-specific patterns here
            ],
            'employer': [
                # Add HomeLink-specific patterns here
            ],
            'injury_date': [
                # Add HomeLink-specific patterns here
            ],
            'injury_details': [
                # Add HomeLink-specific patterns here
            ],
            'physician_name': [
                # Add HomeLink-specific patterns here
            ],
            'physician_npi': [
                # Add HomeLink-specific patterns here
            ],
            'provider_name': [
                # Add HomeLink-specific patterns here
            ],
            'authorized_sessions': [
                # Add HomeLink-specific patterns here
            ],
            'authorization_date': [
                # Add HomeLink-specific patterns here
            ],
            'rx_expiration_date': [
                # Add HomeLink-specific patterns here
            ],
            'procedure': [
                # Add HomeLink-specific patterns here
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

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using pypdfium2
        
        :param pdf_path: Path to the PDF file
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
                text_page = page.get_textpage()
                page_text = text_page.get_text_bounded()
                
                # Append page text
                extracted_text += page_text + "\n"
                
                # Debug: Save extracted text to file for analysis
                if 'CorvelAuth.pdf' in pdf_path:
                    with open('corvel_debug.txt', 'w', encoding='utf-8') as f:
                        f.write(extracted_text)
                    print("\n=== Corvel PDF Content Saved to corvel_debug.txt ===")
            
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
        full_text = self.extract_text_from_pdf(input_source) if is_pdf else input_source
        
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

    def save_to_database(self, extracted_info: Dict[str, Optional[str]]) -> str:
        """
        Save extracted information to database
        
        :param extracted_info: Dictionary of extracted information
        :return: Success/error message
        """
        try:
            with Session(engine) as session:
                # Split patient name into first and last name
                patient_name = extracted_info.get('patient_name', '').strip()
                name_parts = patient_name.split()
                first_name = name_parts[0] if name_parts else "Unknown"
                last_name = name_parts[-1] if len(name_parts) > 1 else "Unknown"
                middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else None

                # Convert date string to date object
                dob = None
                if extracted_info.get('patient_dob'):
                    try:
                        dob = datetime.strptime(extracted_info['patient_dob'], '%m/%d/%Y').date()
                    except ValueError:
                        logger.warning(f"Invalid date format: {extracted_info['patient_dob']}")

                # Create patient record
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

                # Create provider record if provider information is available
                provider = None
                if extracted_info.get('provider_name'):
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

                # Create authorization record if we have the required information
                if provider and extracted_info.get('case_id') and extracted_info.get('service_type'):
                    # Convert service type to enum
                    service_type = ServiceType.OTHER  # Default to OTHER
                    service_type_str = extracted_info['service_type'].lower().replace(' ', '_')
                    try:
                        service_type = ServiceType(service_type_str)
                    except ValueError:
                        logger.warning(f"Invalid service type: {extracted_info['service_type']}, defaulting to OTHER")

                    # Get injury date or use current date as fallback
                    initial_eval_date = None
                    if extracted_info.get('injury_date'):
                        try:
                            initial_eval_date = datetime.strptime(extracted_info['injury_date'], '%m/%d/%Y').date()
                        except ValueError:
                            logger.warning(f"Invalid injury date format: {extracted_info['injury_date']}")
                    if not initial_eval_date:
                        initial_eval_date = datetime.now(timezone.utc).date()

                    # Get number of authorized visits
                    num_visits = int(extracted_info.get('authorized_sessions', 1))

                    authorization = Authorization(
                        patient_id=patient.patient_id,
                        provider_id=provider.provider_id,
                        claim_number=extracted_info.get('claim_number', ''),
                        num_authorized_visits=num_visits,
                        service_type=service_type,
                        initial_evaluation_date=initial_eval_date,
                        status=AuthorizationStatus.PENDING,
                        notes=f"Case ID: {extracted_info.get('case_id')}",
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

    def extract_and_save_info(pdf_file, text_input, pdf_type, save_to_db):
        """
        Process input, extract information, and optionally save to database
        """
        # Determine input source
        if pdf_file and text_input:
            return "Please use either PDF upload OR text input, not both.", None, None
        
        try:
            # PDF file processing
            if pdf_file:
                logger.debug(f"PDF File received: {pdf_file}")
                
                # Verify file exists and is a PDF
                if not os.path.exists(pdf_file):
                    logger.error(f"File does not exist: {pdf_file}")
                    return "File does not exist.", None, None
                
                if not pdf_file.lower().endswith('.pdf'):
                    logger.error(f"Not a PDF file: {pdf_file}")
                    return "Please upload a valid PDF file.", None, None
                
                # Check if PDF type is selected
                if not pdf_type:
                    logger.error("No PDF type selected")
                    return "Please select a PDF type (OneCall, Corvel, or HomeLink).", None, None
                
                # Extract information from PDF
                extracted_info = extractor.extract_key_information(pdf_file, is_pdf=True, pdf_type=pdf_type)
                input_source = pdf_file
            
            # Text input processing
            elif text_input:
                logger.debug("Text input received")
                extracted_info = extractor.extract_key_information(text_input, is_pdf=False)
                input_source = "Text Input"
            
            else:
                return "Please upload a PDF or enter text.", None, None
            
            # Format results for display
            result_text = "Extracted Information:\n"
            result_text += "\n".join([f"{key.replace('_', ' ').title()}: {value or 'Not Found'}" 
                                       for key, value in extracted_info.items()])
            
            # Create DataFrame for tabular view
            df = pd.DataFrame.from_dict(extracted_info, orient='index', columns=['Value'])
            df.index.name = 'Key'
            df = df.reset_index()
            
            # Save to database if requested
            if save_to_db:
                save_result = extractor.save_to_database(extracted_info)
                result_text += f"\n\n{save_result}"
            
            logger.info("Information extraction successful")
            return result_text, df, input_source
        
        except Exception as e:
            logger.error(f"Error processing input: {str(e)}")
            return f"Error processing input: {str(e)}", None, None

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
                
                # Extract and Save buttons
                with gr.Row():
                    extract_btn = gr.Button("Extract Information", variant="primary")
                    save_btn = gr.Button("Save to Database", variant="secondary")
                
                # Outputs
                text_output = gr.Textbox(label="Extracted Text", lines=10)
                df_output = gr.DataFrame(label="Extracted Information")
            
            with gr.Column(scale=1):
                # PDF Preview (only visible for PDF uploads)
                pdf_preview = PDF(label="PDF Preview", interactive=True)

        # Event handlers
        pdf_input.upload(
            fn=lambda file: file, 
            inputs=pdf_input, 
            outputs=pdf_preview
        )
        
        extract_btn.click(
            fn=lambda pdf, text, type: extract_and_save_info(pdf, text, type, False),
            inputs=[pdf_input, text_input, pdf_type], 
            outputs=[text_output, df_output, pdf_preview]
        )
        
        save_btn.click(
            fn=lambda pdf, text, type: extract_and_save_info(pdf, text, type, True),
            inputs=[pdf_input, text_input, pdf_type], 
            outputs=[text_output, df_output, pdf_preview]
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