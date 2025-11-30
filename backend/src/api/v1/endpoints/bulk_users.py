from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import csv
import io
import secrets
import string
from typing import Dict, Any
from src import crud, models
from src.schemas import user as user_schema
from src.api import dependencies

router = APIRouter()

def generate_secure_password(length: int = 12) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in string.punctuation for c in password)):
            return password

@router.post("/bulk-import", tags=["users"])
def bulk_import_users(
    file: UploadFile = File(...),
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin),
) -> Dict[str, Any]:
    """
    Bulk import users from a CSV file.
    The CSV should have columns: email, first_name, last_name, user_type
    """
    if not file.filename.endswith(('.csv',)):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Read the file content
    try:
        contents = file.file.read().decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Please upload a UTF-8 encoded CSV.")
    finally:
        file.file.close()
    
    # Parse the CSV
    csv_file = io.StringIO(contents)
    csv_data = csv.DictReader(csv_file)
    
    # Required fields
    required_fields = {'email', 'first_name', 'last_name'}
    
    # Validate CSV structure
    if not csv_data.fieldnames or not required_fields.issubset(set(csv_data.fieldnames)):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain the following columns: {', '.join(required_fields)}"
        )
    
    created_users = []
    failed_users = []
    
    # Reset file pointer to read rows
    csv_file.seek(0)
    csv_data = csv.DictReader(csv_file)
    
    for row_num, row in enumerate(csv_data, start=2):  # start=2 because CSV rows start from 2 (header is 1)
        try:
            email = row.get('email', '').strip()
            if not email:
                failed_users.append({"row": row_num, "email": "N/A", "error": "Email is required"})
                continue

            # Generate a secure random password
            generated_password = generate_secure_password()
            
            # Prepare user data
            user_in = user_schema.UserCreate(
                email=email,
                first_name=row.get('first_name', '').strip(),
                last_name=row.get('last_name', '').strip(),
                user_type=row.get('user_type', 'employee').strip(),  # Default to employee if not specified
                password=generated_password,
                is_active=True,  # By default, imported users are active
            )
            
            # Check if user already exists
            existing_user = crud.user.get_by_email(db, email=user_in.email)
            if existing_user:
                failed_users.append({
                    "row": row_num,
                    "email": user_in.email,
                    "error": "User with this email already exists"
                })
                continue
            
            # Create the user
            user = crud.user.create(db, obj_in=user_in)
            created_users.append({
                "id": user.id,
                "email": user.email,
                "employee_id": user.employee_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_type": user.user_type,
                "temporary_password": generated_password  # Return the password so admin can distribute it
            })
            
        except Exception as e:
            failed_users.append({
                "row": row_num,
                "email": row.get('email', 'Unknown'),
                "error": str(e)
            })
    
    return {
        "message": f"Bulk import completed. {len(created_users)} users created, {len(failed_users)} failed.",
        "created_users": created_users,
        "failed_users": failed_users
    }