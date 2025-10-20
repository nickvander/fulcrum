import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from pathlib import Path
import shutil

from alembic import command
from alembic.config import Config

from src.main import app
from src.database import get_db
from src.config import settings
from src import models
from src.models.product import Product, ProductImage
from src.crud import crud_product, crud_product_image
from src.schemas.product import ProductCreate, ProductImageCreate

# Use the database URL from the environment settings
engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def create_test_database():
    """
    Create the test database and tables once per session using Alembic.
    """
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.commit()

    # Path to alembic.ini
    alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
    
    # Create an Alembic configuration object
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(Path(__file__).parent.parent / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    # Upgrade the database to the latest revision
    command.upgrade(alembic_cfg, "head")
    
    yield
    
    # Downgrade the database to the base revision
    command.downgrade(alembic_cfg, "base")
    with engine.connect() as connection:
        connection.execute(text("DROP TYPE IF EXISTS ordersource CASCADE;"))
        connection.commit()


@pytest.fixture(scope="function")
def db(create_test_database):
    """
    Provides a transactional database session for each test function.
    Rolls back all changes after the test completes.
    """
    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope="function")
def client(db: Session):
    """
    Provides a TestClient that uses the transactional db session.
    """
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def test_product(db: Session) -> Product:
    """
    Creates a sample product in the database for testing.
    """
    product_in = ProductCreate(
        name="Test Product",
        description="A product for testing",
        sku="TESTSKUFIXTURE",
        default_resale_price=19.99,
        cost_price=10.0,
    )
    return crud_product.product.create(db=db, obj_in=product_in)

@pytest.fixture(scope="function")
def test_product_with_image(db: Session, test_product: Product) -> ProductImage:
    """
    Creates a product with a dummy image file and database record.
    Cleans up the created file afterwards.
    """
    # Create a dummy file
    uploads_dir = Path("uploads/product_images") / str(test_product.id)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / "test_fixture_image.jpg"
    with open(file_path, "wb") as f:
        f.write(b"dummy image data")

    # Create the database record
    image_in = ProductImageCreate(
        product_id=test_product.id,
        image_path=str(file_path)
    )
    db_image = crud_product_image.product_image.create(db=db, obj_in=image_in)

    yield db_image

    # Teardown: remove the created file and directory
    if os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(uploads_dir):
        try:
            # Use rmtree to remove the directory if it's empty
            shutil.rmtree(uploads_dir)
        except OSError:
            # Directory might not be empty if other tests created files
            pass


@pytest.fixture(scope="function")
def test_admin_user(db: Session) -> models.User:
    """
    Creates a test admin user.
    """
    from src.schemas.user import UserCreate
    from src.crud import user
    
    user_in = UserCreate(
        email="admin@test.com",
        password="TestPassword123!",
        is_superuser=True,
        user_type="admin",
        first_name="Admin",
        last_name="User"
    )
    return user.create(db=db, obj_in=user_in)


@pytest.fixture(scope="function")
def test_employee_user(db: Session) -> models.User:
    """
    Creates a test employee user.
    """
    from src.schemas.user import UserCreate
    from src.crud import user
    
    user_in = UserCreate(
        email="employee@test.com",
        password="TestPassword123!",
        user_type="employee",
        first_name="Employee",
        last_name="User"
    )
    return user.create(db=db, obj_in=user_in)


@pytest.fixture(scope="function")
def test_customer_user(db: Session) -> models.User:
    """
    Creates a test customer user.
    """
    from src.schemas.user import UserCreate
    from src.crud import user
    
    user_in = UserCreate(
        email="customer@test.com",
        password="TestPassword123!",
        user_type="customer",
        first_name="Customer",
        last_name="User"
    )
    return user.create(db=db, obj_in=user_in)
