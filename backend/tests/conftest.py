import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from pathlib import Path
import shutil

from src.main import app
from src.database import get_db
from src.models.base import Base
from src.config import settings
from src.models.product import Product, ProductImage
from src.crud import crud_product, crud_product_image
from src.schemas.product import ProductCreate, ProductImageCreate

# Use the database URL from the environment settings
engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """
    Create the test database and tables once per session.
    """
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.commit()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    with engine.connect() as connection:
        connection.execute(text("DROP TYPE IF EXISTS ordersource CASCADE;"))
        connection.commit()

@pytest.fixture(scope="function")
def db():
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