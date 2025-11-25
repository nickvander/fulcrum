from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import csv
import io
from src import crud, models
from src.schemas import user as user_schema
from src.api import dependencies

router = APIRouter()


@router.post("/bulk-import", tags=["users"])
def bulk_import_users(
    file: UploadFile = File(...),
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin),
) -> dict:
    """
    Bulk import users from a CSV file.
    The CSV should have columns: email, first_name, last_name, user_type
    """
    if not file.filename.endswith(('.csv',)):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Read the file content
    contents = file.file.read().decode("utf-8")
    file.file.close()
    
    # Parse the CSV
    csv_data = csv.DictReader(io.StringIO(contents))
    
    # Required fields
    required_fields = {'email', 'first_name', 'last_name'}
    
    # Validate CSV structure
    if not all(field in csv_data.fieldnames for field in required_fields):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain the following columns: {', '.join(required_fields)}"
        )
    
    created_users = []
    failed_users = []
    
    for row_num, row in enumerate(csv_data, start=2):  # start=2 because CSV rows start from 2 (header is 1)
        try:
            # Set a default password for imported users that they'll need to change
            default_password = "TempPass123!"
            
            # Prepare user data
            user_in = user_schema.UserCreate(
                email=row['email'].strip(),
                first_name=row['first_name'].strip(),
                last_name=row['last_name'].strip(),
                user_type=row.get('user_type', 'employee'),  # Default to employee if not specified
                password=default_password,
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
                "user_type": user.user_type
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