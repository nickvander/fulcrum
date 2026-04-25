import logging

from src.database import SessionLocal
from src.core.security import get_password_hash
from src.models.user import User

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_full():
    db = SessionLocal()
    try:
        logger.info("Starting clean seeding...")

        # 1. Clear database
        from src.scripts.seed_agujetas import seed_agujetas
        seed_agujetas()
        
        # 2. Seed Users (ensure they exist)
        logger.info("--- Seeding Users ---")
        admin_email = "admin@example.com"
        admin_password = "SecurePass123!"
        
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            logger.info(f"Creating superuser: {admin_email}")
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                first_name="Admin",
                last_name="User",
                user_type="admin",
                is_active=True,
                is_superuser=True,
                role="admin",
                employee_id="ADM000001"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        else:
            logger.info(f"Superuser {admin_email} already exists.")
            admin_user = existing_admin

        # Extra Users
        extra_users = [
            {"email": "manager@example.com", "role": "admin", "first_name": "Store", "last_name": "Manager", "emp_id": "EMP000002"},
            {"email": "staff@example.com", "role": "employee", "first_name": "Support", "last_name": "Staff", "emp_id": "EMP000003"},
        ]
        
        for u_data in extra_users:
            existing_u = db.query(User).filter(User.email == u_data["email"]).first()
            if not existing_u:
                new_u = User(
                    email=u_data["email"],
                    hashed_password=get_password_hash("SecurePass123!"),
                    first_name=u_data["first_name"],
                    last_name=u_data["last_name"],
                    user_type=u_data["role"],
                    is_active=True,
                    is_superuser=False,
                    role=u_data["role"],
                    employee_id=u_data["emp_id"]
                )
                db.add(new_u)
                logger.info(f"Created user: {u_data['email']}")
        db.commit()

        logger.info("Clean seeding completed successfully.")

    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_full()
