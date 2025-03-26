import gradio as gr
import pandas as pd
import re
import logging
import os
import io
from typing import Dict, List, Optional
from gradio_pdf import PDF

# PDF extraction library
import pypdfium2 as pdfium

class MedicalPDFExtractor:
    def __init__(self, 
                 key_patterns: Dict[str, List[str]] = None):
        """
        Initialize PDF extractor with extraction methods
        
        :param key_patterns: Dictionary of key extraction patterns
        """
        # Default key extraction patterns
        self.default_patterns = {
            'patient_name': [
                r'Legal\s*Name\s*[:]*\s*([^\n:]+)',
                r'Patient\s*Name\s*[:]*\s*([^\n:]+)',
                r'Name\s*[:]*\s*([^\n:]+)',
            ],
            'claim_number': [
                r'Claim\s*Number\s*[:]*\s*(\S+)',
                r'Claim\s*#\s*[:]*\s*(\S+)',
            ],
            'date_of_service': [
                r'Electronically\s*signed\s*by:.*\n.*\n(\d{1,2}/\d{1,2}/\d{4})',
                r'Date\s*of\s*Service\s*[:]*\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'date_of_birth': [
                r'Date\s*of\s*Birth\s*[:]*\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DOB\s*[:]*\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'authorized_sessions': [
                r'(\d+)\s*session',
                r'Massage\s*Therapy\s*.*?(\d+)\s*session',
                r'Authorized\s*Sessions\s*[:]*\s*(\d+)',
            ],
            'insurance_provider': [
                r'Carrier\s*Name\s*[:]*\s*([^\n:]+)',
                r'Insurance\s*Provider\s*[:]*\s*([^\n:]+)',
            ],
            'diagnosis_code': [
                r'DIAGNOSIS\s*ICD-CODE\s*\n\s*(\w+\.\d+)',
                r'Diagnosis\s*Code\s*[:]*\s*(\w+\.\d+)',
            ],
            'authorization_status': [
                r'Notification\s*for\s*Pre-Authorized\s*Services',
                r'Authorization\s*Status\s*[:]*\s*([^\n:]+)',
            ]
        }
        
        # Update with custom patterns if provided
        self.key_patterns = self.default_patterns if key_patterns is None else {**self.default_patterns, **key_patterns}

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
            
            return extracted_text
        
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""

    def extract_key_information(self, pdf_path: str) -> Dict[str, Optional[str]]:
        """
        Extract key information from PDF using regex patterns with enhanced debugging
        
        :param pdf_path: Path to the PDF file
        :return: Dictionary of extracted information
        """
        # Extract text from PDF
        full_text = self.extract_text_from_pdf(pdf_path)
        
        # Extract information using patterns
        extracted_info = {}
        for key, patterns in self.key_patterns.items():
            extracted_info[key] = None
            for pattern in patterns:
                try:
                    match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    if match:
                        # Try to get the first capturing group, or the entire match if no groups
                        extracted_value = match.group(1) if match.groups() else match.group(0)
                        extracted_info[key] = extracted_value.strip()
                        print(f"Matched {key} with pattern: {pattern}")
                        break
                except Exception as e:
                    print(f"Error matching {key} with pattern {pattern}: {e}")
        
        # Additional debugging: print full text if no matches found
        if all(value is None for value in extracted_info.values()):
            print("No matches found. Full PDF text:")
            print(full_text)
        
        return extracted_info

def create_pdf_extractor_app():
    """
    Create Gradio app for PDF information extraction
    """
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Initialize extractor
    extractor = MedicalPDFExtractor()

    def extract_info(pdf_file):
        """
        Process PDF and return extracted information
        """
        logger.debug(f"PDF File received: {pdf_file}")
        
        if pdf_file is None:
            logger.warning("No PDF file uploaded")
            return "Please upload a PDF file.", None, None
        
        try:
            # Verify file exists and is a PDF
            if not os.path.exists(pdf_file):
                logger.error(f"File does not exist: {pdf_file}")
                return "File does not exist.", None, None
            
            if not pdf_file.lower().endswith('.pdf'):
                logger.error(f"Not a PDF file: {pdf_file}")
                return "Please upload a valid PDF file.", None, None
            
            # Log file details
            file_stats = os.stat(pdf_file)
            logger.debug(f"File size: {file_stats.st_size} bytes")

            # Extract information
            extracted_info = extractor.extract_key_information(pdf_file)
            
            # Format results for display
            result_text = "Extracted Information:\n"
            result_text += "\n".join([f"{key.replace('_', ' ').title()}: {value or 'Not Found'}" 
                                       for key, value in extracted_info.items()])
            
            # Create DataFrame for tabular view
            df = pd.DataFrame.from_dict(extracted_info, orient='index', columns=['Value'])
            df.index.name = 'Key'
            df = df.reset_index()
            
            logger.info("PDF extraction successful")
            return result_text, df, pdf_file
        
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return f"Error processing PDF: {str(e)}", None, None

    # Create Gradio interface
    with gr.Blocks(title="Medical PDF Information Extractor") as demo:
        gr.Markdown("# Medical Authorization PDF Information Extractor")
        
        with gr.Row():
            with gr.Column(scale=1):
                pdf_input = gr.File(label="Upload PDF", file_types=['.pdf'])
                extract_btn = gr.Button("Extract Information", variant="primary")
                
                # Text and DataFrame outputs
                text_output = gr.Textbox(label="Extracted Text", lines=10)
                df_output = gr.DataFrame(label="Extracted Information")
            
            with gr.Column(scale=1):
                # PDF Preview using PDF Viewer
                pdf_preview = PDF(label="PDF Preview", interactive=True)

        
        # Set up event handlers
        pdf_input.upload(
            fn=lambda file: file, 
            inputs=pdf_input, 
            outputs=pdf_preview
        )
        
        extract_btn.click(
            fn=extract_info, 
            inputs=pdf_input, 
            outputs=[text_output, df_output, pdf_preview]
        )
        
        # Add some explanatory text
        gr.Markdown("""
        ### How to Use
        1. Upload a medical authorization PDF
        2. Preview the PDF
        3. Click "Extract Information"
        4. View extracted details in text and table format
        
        #### Notes
        - Uses PyPDFium2 for PDF text extraction
        - Supports various PDF formats
        - Cross-platform compatibility
        """)

    return demo

# Launch the app
if __name__ == "__main__":
    demo = create_pdf_extractor_app()
    demo.launch(debug=True, share=True)