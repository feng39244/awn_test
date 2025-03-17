#!/bin/bash

# Initialize Alembic (first time only)
# alembic init migrations

# Create a new migration
alembic revision --autogenerate -m "create_user_table"

# Apply migrations to the database
alembic upgrade head

# Downgrade to previous version
# alembic downgrade -1

# Downgrade to specific revision
# alembic downgrade <revision_id>

# Get current revision
# alembic current

# Show migration history
# alembic history --verbose