from pdfrw import PdfReader, PdfWriter, PageMerge
from pdfrw import PdfReader, PdfWriter, PdfName, PdfString, IndirectPdfDict, PdfObject

# Define input and output file paths
input_pdf_path = "form-cms1500.pdf"  # Half-filled form
#input_pdf_path = "CMS1500-0212-MDCW.pdf"
#input_pdf_path = "massage_filled.pdf"

output_pdf_path = "Filled_CMS_15002.pdf"  # Output fully filled form

# Load the PDF form
pdf = PdfReader(input_pdf_path)
annotations = pdf.pages[0]['/Annots']

for annot in pdf.pages[0]['/Annots']:
    print(f"Field Name: {annot['/T']}, Type: {annot['/FT']}, Position: {annot['/Rect']}")

doc_fields = {
    'doc_name': 'All Wellness Now,LLC.',
    'doc_street': '720 Magnolia Ave.,#B3',
    'doc_location': 'Corona CA 92879',
    'doc_phone area': '951',
    'doc_phone': '371-8888',
    'tax_id': '45-0941589',
}

patient_fields = {
    'pt_name': 'John Doe',
    'birth_mm': '01',
    'birth_dd': '15',
    'birth_yy': '1985',
    'pt_street': '1234 Elm Street',
    'pt_city': 'Los Angeles',
    'pt_state': 'CA',
    'pt_zip': '90001',
    'pt_AreaCode': '310',
    'pt_phone': '555-1234',
    'pt_signature': 'ON FILE',
    'pt_date': 'Not provided',
}

insurance_fields = {
    'insurance_name': 'MEDICARE | MEDICAID | TRICARE | CHWPA',
    'insurance_address': '1234 Elm Street',
    'insurance_address2': 'Los Angeles',
    'insurance_city_state_zip': 'CA 90001',
}

insurer_fields = {
    'insurance_id': '1962792549',
    'ins_name': 'John Doe',
    'ins_dob_mm': 'Not provided',
    'ins_dob_dd': 'Not provided',
    'ins_dob_yy': 'Not provided',
    'ins_street': '1234 Elm Street',
    'ins_city': 'Los Angeles',
    'ins_state': 'CA',
    'ins_zip': '90001',
    'ins_phone area': '310',
    'ins_phone': '555-1234',
    'ins_policy': 'Not provided',
    'ins_plan_name': 'Not provided',  # Item 1 options, no selection specified
    'other_ins_name': 'Not provided',
    'other_ins_policy': 'Not provided',
    'other_ins_plan_name': 'Not provided',
    'ins_signature': 'ON FILE',
}


claim_fields = {
    'cur_ill_mm': 'Not provided',
    'cur_ill_dd': 'Not provided',
    'cur_ill_yy': 'Not provided',
    'ref_physician': 'Not provided',
    'id_physician': 'Not provided',
    '96': 'Not provided', # additional claim information
    '99icd': 'Not provided',  #icd 9 ind e
    'diagnosis1': 'Not provided',
    'diagnosis2': 'Not provided',
    'diagnosis3': 'Not provided',
    'diagnosis4': 'Not provided',
    'diagnosis5': 'Not provided',
    'diagnosis6': 'Not provided',
    'diagnosis7': 'Not provided',
    'diagnosis8': 'Not provided',
    'diagnosis9': 'Not provided',
    'diagnosis10': 'Not provided',
    'diagnosis11': 'Not provided',
    'diagnosis12': 'Not provided',
    'prior_auth': 'Not provided',

}

massage_treatment_therapist_fields = {
    'local1a': 'Not provided', # therapist SSN
    'local1': 'Not provided', # therapist NPI
    'loca2a': 'Not provided', # therapist SSN
    'local2': 'Not provided', # therapist NPI
    'local3a': 'Not provided', # therapist SSN
    'local3': 'Not provided', # therapist NPI
    'local4a': 'Not provided', # therapist SSN
    'local4': 'Not provided', # therapist NPI
    'local5a': 'Not provided', # therapist SSN
    'local5': 'Not provided', # therapist NPI
    'local6a': 'Not provided', # therapist SSN
    'local6': 'Not provided', # therapist NPI
}

massage_treatment_fields = {
    'emg1': 'Not provided',
    'sv1_mm_from': 'Not provided',
    'sv1_dd_from': 'Not provided',
    'sv1_yy_from': 'Not provided',
    'sv1_mm_end': 'Not provided',
    'sv1_dd_end': 'Not provided',
    'sv1_yy_end': 'Not provided',
    'place1': 'Not provided',
    'type1': 'Not provided',
    'cpt1': 'Not provided',
    'mod1': 'Not provided',
    'mod1a': 'Not provided',
    'mod1b': 'Not provided',
    'mod1c': 'Not provided',
    'diag1': 'Not provided',
    'ch1': 'Not provided',
    '135': 'Not provided',  # Unclear field reference
    'day1': 'Not provided',
    'epsdt1': 'Not provided',
    'Suppla': 'Not provided',
    'emg2': 'Not provided',
    'sv2_mm_from': 'Not provided',
    'sv2_dd_from': 'Not provided',
    'sv2_yy_from': 'Not provided',
    'sv2_mm_end': 'Not provided',
    'sv2_dd_end': 'Not provided',
    'sv2_yy_end': 'Not provided',
    'place2': 'Not provided',
    'type2': 'Not provided',
    'cpt2': 'Not provided',
    'mod2': 'Not provided',
    'mod2a': 'Not provided',
    'mod2b': 'Not provided',
    'mod2c': 'Not provided',
    'diag2': 'Not provided',
    'ch2': 'Not provided',
    '157': 'Not provided',  # Unclear field reference
    'day2': 'Not provided',
    'plan2': 'Not provided',
    'Supplb': 'Not provided',
    'emg3': 'Not provided',
    'sv3_mm_from': 'Not provided',
    'sv3_dd_from': 'Not provided',
    'sv3_yy_from': 'Not provided',
    'sv3_mm_end': 'Not provided',
    'sv3_dd_end': 'Not provided',
    'sv3_yy_end': 'Not provided',
    'place3': 'Not provided',
    'type3': 'Not provided',
    'cpt3': 'Not provided',
    'mod3': 'Not provided',
    'mod3a': 'Not provided',
    'mod3b': 'Not provided',
    'mod3c': 'Not provided',
    'diag3': 'Not provided',
    'ch3': 'Not provided',
    '179': 'Not provided',  # Unclear field reference
    'day3': 'Not provided',
    'plan3': 'Not provided',
    'Supplc': 'Not provided',
    'emg4': 'Not provided',
    'sv4_mm_from': 'Not provided',
    'sv4_dd_from': 'Not provided',
    'sv4_yy_from': 'Not provided',
    'sv4_mm_end': 'Not provided',
    'sv4_dd_end': 'Not provided',
    'sv4_yy_end': 'Not provided',
    'place4': 'Not provided',
    'type4': 'Not provided',
    'cpt4': 'Not provided',
    'mod4': 'Not provided',
    'mod4a': 'Not provided',
    'mod4b': 'Not provided',
    'mod4c': 'Not provided',
    'diag4': 'Not provided',
    'ch4': 'Not provided',
    '201': 'Not provided',  # Unclear field reference
    'day4': 'Not provided',
    'plan4': 'Not provided',
    'Suppld': 'Not provided',
    'emg5': 'Not provided',
    'sv5_mm_from': 'Not provided',
    'sv5_dd_from': 'Not provided',
    'sv5_yy_from': 'Not provided',
    'sv5_mm_end': 'Not provided',
    'sv5_dd_end': 'Not provided',
    'sv5_yy_end': 'Not provided',
    'place5': 'Not provided',
    'type5': 'Not provided',
    'cpt5': 'Not provided',
    'mod5': 'Not provided',
    'mod5a': 'Not provided',
    'mod5b': 'Not provided',
    'mod5c': 'Not provided',
    'diag5': 'Not provided',
    'ch5': 'Not provided',
    '223': 'Not provided',  # Unclear field reference
    'day5': 'Not provided',
    'plan5': 'Not provided',
    'Supple': 'Not provided',
    'emg6': 'Not provided',
    'sv6_mm_from': 'Not provided',
    'sv6_dd_from': 'Not provided',
    'sv6_yy_from': 'Not provided',
    'sv6_mm_end': 'Not provided',
    'sv6_dd_end': 'Not provided',
    'sv6_yy_end': 'Not provided',
    'place6': 'Not provided',
    'type6': 'Not provided',
    'cpt6': 'Not provided',
    'mod6': 'Not provided',
    'mod6a': 'Not provided',
    'mod6b': 'Not provided',
    'mod6c': 'Not provided',
    'diag6': 'Not provided',
    'ch6': 'Not provided',
    '245': 'Not provided',  # Unclear field reference
    'day6': 'Not provided',
    'plan6': 'Not provided',
    'local6': 'Not provided'
}


massage_fields = {
    'NUCC USE': 'Not provided',
    '40': 'Not provided',  # Unclear field reference
    'accident_place': 'Not provided',
    '57': 'Not provided',  # Unclear field reference
    '58': 'Not provided',  # Unclear field reference
    '41': 'Not provided',  # Unclear field reference 
    '50': 'Not provided',  # Unclear field reference
    '73': 'Not provided',  # Unclear field reference
    '74': 'Not provided',  # Unclear field reference
    'sim_ill_mm': 'Not provided',
    'sim_ill_dd': 'Not provided',
    'sim_ill_yy': 'Not provided',
    'work_mm_from': 'Not provided',
    'work_dd_from': 'Not provided',
    'work_yy_from': 'Not provided',
    'work_mm_end': 'Not provided',
    'work_dd_end': 'Not provided',
    'work_yy_end': 'Not provided',
    'physician number 17a1': 'Not provided',
    'physician number 17a': 'Not provided',
    '85': 'Not provided',  # Unclear field reference
    'hosp_mm_from': 'Not provided',
    'hosp_dd_from': 'Not provided',
    'hosp_yy_from': 'Not provided',
    'hosp_mm_end': 'Not provided',
    'hosp_dd_end': 'Not provided',
    'hosp_yy_end': 'Not provided',
    'charge': 'Not provided',
    'medicaid_resub': 'Not provided',
    'original_ref': 'Not provided',
    'Suppl': 'Not provided',
    '276': 'Not provided',  # Unclear field reference
    
    'pt_account': 'Not provided',
    't_charge': 'Not provided',
    'amt_paid': 'Not provided',
    'fac_name': 'MedRisk',  # Assuming this is the facility/billing provider name (Item 33)
    'fac_street': 'P.O BOX 14229',  # Item 33 address
    'physician_signature': 'Not provided',
    'fac_location': 'LEXINGTON KY 40512',  # Item 33 city, state, ZIP
    'physician_date': 'Not provided',
    'pin1': 'Not provided',
    'grp1': 'Not provided',
    'pin': '1962792549',
    'grp': 'Not provided',
    'Clear Form': 'Not provided',  # Likely not a field, possibly a button
    'plan1': 'Not provided',
    'epsdt2': 'Not provided',
    'epsdt3': 'Not provided',
    'epsdt4': 'Not provided',
    'epsdt6': 'Not provided',
    'epsdt5': 'Not provided'
}
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
all_fields = {}
for annot in annotations:
    if annot['/T']:  # Check if it has a field name
        field_name = annot['/T'][1:-1]  # Extract field name (e.g., "InsuredID")
        all_fields[field_name] = ""
        print(f"Field: {field_name}, Type: {annot['/FT']}, Value Before: {annot['/V']}")
        annot.update({
                PdfName('V'): PdfString.encode(field_name),
                PdfName('Ff'): PdfString.encode('0')  # Try 0 instead of 1
            })
        print(f"Value After: {annot['/V']}")

print(f"All fields: {all_fields.keys()}")

# Set NeedAppearances to True
if pdf.Root.AcroForm is None:
    pdf.Root.AcroForm = IndirectPdfDict()
pdf.Root.AcroForm.update({PdfName('NeedAppearances'): PdfObject('true')})
# Write the modified PDF
PdfWriter(output_pdf_path, trailer=pdf).write()

print(f"Filled CMS-1500 form saved as {output_pdf_path}")
