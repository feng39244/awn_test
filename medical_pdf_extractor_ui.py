import gradio as gr
import pandas as pd
import re
import logging
import os
import io
from typing import Dict, List, Optional
from gradio_pdf import PDF
import pypdfium2 as pdfium

class MedicalInfoExtractor:
    def __init__(self, 
                 key_patterns: Dict[str, List[str]] = None):
        """
        Initialize extractor with extraction methods
        
        :param key_patterns: Dictionary of key extraction patterns
        """
        # Updated default key extraction patterns
        self.default_patterns = {
            'patient_name': [
                r'Name:\s*([^\n]+)',
                r'Name\s*([^\n]+)',
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
                r'Address 1:\s*([^\n]+)\nCity/ST/Zip:\s*([^\n]+)',
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

    def extract_key_information(self, input_source: str, is_pdf: bool = False) -> Dict[str, Optional[str]]:
        """
        Extract key information from input source (PDF or text)
        
        :param input_source: Path to PDF or raw text
        :param is_pdf: Flag to indicate if input is a PDF file
        :return: Dictionary of extracted information
        """
        # Extract text based on input type
        full_text = self.extract_text_from_pdf(input_source) if is_pdf else input_source
        
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
            print("No matches found. Full text:")
            print(full_text)
        
        return extracted_info

def create_medical_extractor_app():
    """
    Create Gradio app for medical information extraction
    """
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Initialize extractor
    extractor = MedicalInfoExtractor()

    def extract_info(pdf_file, text_input):
        """
        Process input and return extracted information
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
                
                # Extract information from PDF
                extracted_info = extractor.extract_key_information(pdf_file, is_pdf=True)
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

        # Event handlers
        pdf_input.upload(
            fn=lambda file: file, 
            inputs=pdf_input, 
            outputs=pdf_preview
        )
        
        extract_btn.click(
            fn=extract_info, 
            inputs=[pdf_input, text_input], 
            outputs=[text_output, df_output, pdf_preview]
        )
        
        # Explanatory text
        gr.Markdown("""
        ### How to Use
        1. Choose between PDF Upload or Text Input
        2. Upload PDF or paste text
        3. Click "Extract Information"
        4. View extracted details in text and table format
        
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