# FastAPI PostgreSQL Authentication App

A simple FastAPI web application with PostgreSQL database backend that implements user authentication with email and password.

## Overview

This application provides:

- User registration with email and password
- Secure password hashing using bcrypt
- JWT-based authentication
- User role management
- Login timestamp tracking
- Welcome message after successful login
- Database migrations using Alembic

## Technical Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLModel**: ORM for interacting with the database
- **PostgreSQL**: Relational database for storing user information
- **Pydantic**: Data validation and settings management
- **PassLib**: Password hashing library
- **PyJWT**: JSON Web Token implementation
- **Alembic**: Database migration tool

## Database Schema

The application uses a simple User table with the following columns:
- id (primary key)
- email (unique)
- hashed_password
- role
- last_login_time

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Docker and Docker Compose (optional)

### Option 1: Local Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd fastapi-postgres-auth
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: gradio\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up PostgreSQL:
   - Create a database named `userdb`
   - Update the `.env` file with your database credentials

5. Run database migrations:
   ```
   alembic upgrade head
   ```

6. Run the application:
   ```
   uvicorn main:app --reload
   ```

### Option 2: Using Docker Compose

1. Clone the repository:
   ```
   git clone <repository-url>
   cd fastapi-postgres-auth
   ```

2. Build and start the containers:
   ```
   docker-compose up -d
   ```

3. Run migrations inside the container:
   ```
   docker-compose exec web alembic upgrade head
   ```

## Database Migrations

This project uses Alembic for managing database migrations:

- **Create a new migration**: When you change models in `main.py`, create a new migration:
  ```
  alembic revision --autogenerate -m "describe_your_changes"
  ```

- **Apply migrations**:
  ```
  alembic upgrade head
  ```

- **Downgrade database**:
  ```
  alembic downgrade -1  # Go back one revision
  ```

- **View migration history**:
  ```
  alembic history --verbose
  ```

## Usage

Once the application is running, you can access:

- API documentation: http://localhost:8000/docs
- Alternative API documentation: http://localhost:8000/redoc

### Registration

```
POST /register
{
  "email": "user@example.com",
  "password": "strongpassword"
}
```

### Login

```
POST /token
Form data:
  username: user@example.com
  password: strongpassword
```

### Welcome Message

```
GET /welcome
Authorization: Bearer <your-token>
```

### User Information

```
GET /users/me
Authorization: Bearer <your-token>
```

## Security Considerations

- Passwords are hashed using bcrypt before storage
- Authentication is implemented using JWT tokens
- Environment variables are used for sensitive information
- The `.env` file should not be committed to version control in production

## Development

To run tests:
```
pytest
```

## Production Deployment

For production deployment, make sure to:
1. Use a strong, unique SECRET_KEY
2. Configure HTTPS
3. Set appropriate token expiration times
4. Implement rate limiting
5. Consider using a more robust PostgreSQL setup with backups

## Local testing
uvicorn main:app --reload

## Cloud testing
uvicorn main:app --host 0.0.0.0 --port 8000 --reload