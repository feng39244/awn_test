from pdfrw import PdfReader, PdfWriter, PageMerge
from pdfrw import PdfReader, PdfWriter, PdfName, PdfString, IndirectPdfDict, PdfObject

# Define input and output file paths
input_pdf_path = "form-cms1500.pdf"  # Half-filled form
output_pdf_path = "Filled_CMS_1500.pdf"  # Output fully filled form

# Load the PDF form
pdf = PdfReader(input_pdf_path)
annotations = pdf.pages[0]['/Annots']

for annot in pdf.pages[0]['/Annots']:
    print(f"Field Name: {annot['/T']}, Type: {annot['/FT']}, Position: {annot['/Rect']}")

# Define additional fields to be filled (example values)
additional_fields = {
    "pt_name": "John Doe",
    "PatientDOB": "01/15/1985",
    "PatientAddress": "1234 Elm Street",
    "PatientCityStateZip": "Los Angeles, CA 90001",
    "InsuranceID": "ABC1234567",
    "DiagnosisCode1": "M54.5",
    "DiagnosisCode2": "R51",
    "TotalCharge": "$500.00",
    "ProviderSignature": "Dr. Jane Smith",
    "DateSigned": "03/16/2025"
}

# Fill the PDF form
for annot in annotations:
    if annot['/T']:  # Check if it has a field name
        field_name = annot['/T'][1:-1]  # Extract field name (e.g., "InsuredID")
        if field_name in additional_fields:
            print(f"Field: {field_name}, Type: {annot['/FT']}, Value Before: {annot['/V']}")
            print(additional_fields[field_name])
            annot.update({
                PdfName('V'): PdfString.encode(additional_fields[field_name]),
                PdfName('Ff'): PdfString.encode('0')  # Try 0 instead of 1
            })
            print(f"Value After: {annot['/V']}")

# Set NeedAppearances to True
if pdf.Root.AcroForm is None:
    pdf.Root.AcroForm = IndirectPdfDict()
pdf.Root.AcroForm.update({PdfName('NeedAppearances'): PdfObject('true')})
# Write the modified PDF
PdfWriter(output_pdf_path, trailer=pdf).write()

print(f"Filled CMS-1500 form saved as {output_pdf_path}")
