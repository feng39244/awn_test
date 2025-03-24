import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from datetime import datetime
from appointment_service import process_uploaded_appointments
from models import Patient, Provider, Location, Appointment

@pytest.fixture
def mock_session():
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.flush = MagicMock()
    return session

@pytest.fixture
def sample_csv_content():
    return '''Client,Client Number,Mobile,Sex,Gender Identity,Postcode,State,Practitioner,Location,Date,End Time,Appointment Type,Type,Invoice,Appointment Notes,Appointment Flag,Status
John Doe,12345,555-0123,Male,Male,12345,NY,Dr. Smith,Main Clinic,3/08/2025 11:00 AM,12:00 PM,Initial,Regular,INV001,Test notes,None,Pending
Jane Smith,67890,555-4567,Female,Female,67890,CA,Dr. Jones,Branch Clinic,3/09/2025 2:00 PM,3:00 PM,Follow-up,Regular,INV002,Follow-up notes,Priority,Confirmed'''

@pytest.fixture
def mock_upload_file(sample_csv_content):
    class MockUploadFile:
        def __init__(self, content):
            self.file = StringIO(content)
            self.filename = "test.csv"

    return MockUploadFile(sample_csv_content)

def test_process_uploaded_appointments_success(mock_session, mock_upload_file):
    # Arrange
    mock_patient = Mock(patient_id=1)
    mock_provider = Mock(provider_id=1)
    mock_location = Mock(location_id=1)
    
    # Mock the get_or_create functions
    with patch('appointment_service.get_or_create_patient', return_value=mock_patient) as mock_get_patient, \
         patch('appointment_service.get_or_create_provider', return_value=mock_provider) as mock_get_provider, \
         patch('appointment_service.get_or_create_location', return_value=mock_location) as mock_get_location:

        # Act
        result = process_uploaded_appointments(mock_upload_file, True, mock_session)

        # Assert
        assert result["total_processed"] == 2
        assert result["created"] == 2
        assert result["errors"] == 0
        assert len(result["error_details"]) == 0

        # Verify that get_or_create functions were called with correct parameters
        mock_get_patient.assert_any_call(
            session=mock_session,
            client_name="John Doe",
            client_number="12345",
            mobile="555-0123",
            sex="Male",
            gender_identity="Male",
            postcode="12345",
            state="NY"
        )

        mock_get_provider.assert_any_call(
            session=mock_session,
            name="Dr. Smith"
        )

        mock_get_location.assert_any_call(
            session=mock_session,
            location_name="Main Clinic"
        )

        # Verify that appointments were created
        assert mock_session.add.call_count == 2
        assert mock_session.commit.call_count == 1

def test_process_uploaded_appointments_invalid_csv(mock_session):
    # Arrange
    invalid_csv = "Invalid,CSV,Content\nMissing,Fields"
    mock_file = Mock()
    mock_file.file = StringIO(invalid_csv)
    mock_file.filename = "test.csv"

    # Act
    result = process_uploaded_appointments(mock_file, True, mock_session)

    # Assert
    assert result["total_processed"] == 1
    assert result["created"] == 0
    assert result["errors"] == 1
    assert len(result["error_details"]) > 0

def test_process_uploaded_appointments_empty_file(mock_session):
    # Arrange
    empty_csv = ""
    mock_file = Mock()
    mock_file.file = StringIO(empty_csv)
    mock_file.filename = "test.csv"

    # Act
    result = process_uploaded_appointments(mock_file, True, mock_session)

    # Assert
    assert result["total_processed"] == 0
    assert result["created"] == 0
    assert result["errors"] == 0

def test_process_uploaded_appointments_no_headers(mock_session, mock_upload_file):
    # Arrange
    csv_content = '''John Doe,12345,555-0123,Male,Male,12345,NY,Dr. Smith,Main Clinic,3/08/2025 11:00 AM,12:00 PM,Initial,Regular,INV001,Test notes,None,Pending'''
    mock_file = Mock()
    mock_file.file = StringIO(csv_content)
    mock_file.filename = "test.csv"

    mock_patient = Mock(patient_id=1)
    mock_provider = Mock(provider_id=1)
    mock_location = Mock(location_id=1)
    
    # Mock the get_or_create functions
    with patch('appointment_service.get_or_create_patient', return_value=mock_patient), \
         patch('appointment_service.get_or_create_provider', return_value=mock_provider), \
         patch('appointment_service.get_or_create_location', return_value=mock_location):

        # Act
        result = process_uploaded_appointments(mock_file, False, mock_session)

        # Assert
        assert result["total_processed"] == 1
        assert result["created"] == 1
        assert result["errors"] == 0

def test_process_uploaded_appointments_database_error(mock_session, mock_upload_file):
    # Arrange
    mock_session.commit.side_effect = Exception("Database error")
    
    mock_patient = Mock(patient_id=1)
    mock_provider = Mock(provider_id=1)
    mock_location = Mock(location_id=1)
    
    # Mock the get_or_create functions
    with patch('appointment_service.get_or_create_patient', return_value=mock_patient), \
         patch('appointment_service.get_or_create_provider', return_value=mock_provider), \
         patch('appointment_service.get_or_create_location', return_value=mock_location):

        # Act
        result = process_uploaded_appointments(mock_upload_file, True, mock_session)

        # Assert
        assert result["total_processed"] == 2
        assert result["created"] == 0
        assert result["errors"] == 2
        assert len(result["error_details"]) == 2
        assert "Database error" in str(result["error_details"][0])

def test_process_uploaded_appointments_invalid_date_format(mock_session):
    # Arrange
    csv_content = '''Client,Client Number,Mobile,Sex,Gender Identity,Postcode,State,Practitioner,Location,Date,End Time,Appointment Type,Type,Invoice,Appointment Notes,Appointment Flag,Status
John Doe,12345,555-0123,Male,Male,12345,NY,Dr. Smith,Main Clinic,Invalid Date,12:00 PM,Initial,Regular,INV001,Test notes,None,Pending'''
    
    mock_file = Mock()
    mock_file.file = StringIO(csv_content)
    mock_file.filename = "test.csv"

    mock_patient = Mock(patient_id=1)
    mock_provider = Mock(provider_id=1)
    mock_location = Mock(location_id=1)
    
    # Mock the get_or_create functions
    with patch('appointment_service.get_or_create_patient', return_value=mock_patient), \
         patch('appointment_service.get_or_create_provider', return_value=mock_provider), \
         patch('appointment_service.get_or_create_location', return_value=mock_location):

        # Act
        result = process_uploaded_appointments(mock_file, True, mock_session)

        # Assert
        assert result["total_processed"] == 1
        assert result["created"] == 1  # Should still create with default datetime
        assert result["errors"] == 0

def test_process_uploaded_appointments_missing_required_fields(mock_session):
    # Arrange
    csv_content = '''Client,Client Number,Mobile,Sex,Gender Identity,Postcode,State,Practitioner,Location,Date,End Time,Appointment Type,Type,Invoice,Appointment Notes,Appointment Flag,Status
,,,,,,,,,3/08/2025 11:00 AM,,,,,,'''
    
    mock_file = Mock()
    mock_file.file = StringIO(csv_content)
    mock_file.filename = "test.csv"

    # Act
    result = process_uploaded_appointments(mock_file, True, mock_session)

    # Assert
    assert result["total_processed"] == 1
    assert result["created"] == 0
    assert result["errors"] == 1
    assert len(result["error_details"]) == 1 