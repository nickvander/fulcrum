import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from pathlib import Path
import shutil

from src.main import app
from src.database import get_db
from src.models.base import Base
import src.models  # Import all models to ensure they are registered with Base
from src.models.product import Product, ProductImage
from src.crud import crud_product, crud_product_image
from src.schemas.product import ProductCreate, ProductImageCreate

# Default to in-memory SQLite database for testing
DEFAULT_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Check for a test database URL override from environment variables
SQLALCHEMY_DATABASE_URL = os.getenv("TEST_DATABASE_URL", DEFAULT_SQLALCHEMY_DATABASE_URL)

# Create the SQLAlchemy engine based on the determined database URL
if SQLALCHEMY_DATABASE_URL == DEFAULT_SQLALCHEMY_DATABASE_URL:
    # Use StaticPool for SQLite to ensure a single, consistent in-memory database
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Use the default pool for other databases like PostgreSQL
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """
    Creates the test database and tables once per session.
    """
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_engine):
    """
    Provides a transactional database session for each test function.
    Rolls back all changes after the test completes.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    yield db

    db.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """
    Provides a TestClient that uses the transactional db session.
    """

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


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
    image_in = ProductImageCreate(product_id=test_product.id, image_path=str(file_path))
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
