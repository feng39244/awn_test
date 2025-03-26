from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/userdb")

def update_appointments_table():
    # Create engine
    engine = create_engine(DATABASE_URL, echo=True)
    
    # SQL to update the appointments table
    sql_commands = [
        """
        DROP TABLE IF EXISTS appointments CASCADE;
        """,
        """
        CREATE TABLE appointments (
            appointment_id SERIAL PRIMARY KEY,
            patient_id INTEGER REFERENCES patients(patient_id),
            provider_id INTEGER REFERENCES providers(provider_id),
            location_id INTEGER REFERENCES locations(location_id),
            appointment_datetime TIMESTAMP WITHOUT TIME ZONE,
            end_time TIME WITHOUT TIME ZONE,
            appointment_type VARCHAR(50) DEFAULT 'Unknown',
            appointment_subtype VARCHAR(50),
            invoice_number VARCHAR(50),
            notes TEXT,
            flag VARCHAR(50),
            status VARCHAR(20) DEFAULT 'pending',
            client_type VARCHAR(50),
            sex VARCHAR(20),
            gender_identity VARCHAR(50),
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]
    
    # Execute each SQL command
    with engine.connect() as conn:
        for sql in sql_commands:
            conn.execute(text(sql))
            conn.commit()

if __name__ == "__main__":
    update_appointments_table() 