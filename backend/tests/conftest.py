import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
os.environ["TESTING"] = "True"
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
from src.api import dependencies


# Check if running in Bazel
IS_BAZEL = os.environ.get("BAZEL_TEST") == "1"

if IS_BAZEL:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer


# Use the database URL from the environment settings
engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def test_containers():
    """
    Spin up containers if running in Bazel.
    """
    if not IS_BAZEL:
        yield
        return

    # Start Postgres
    postgres = PostgresContainer("postgres:16-alpine", driver="psycopg2")
    postgres.start()
    
    # Enable vector extension
    with postgres.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()

    # Start Redis
    redis = RedisContainer("redis:7-alpine")
    redis.start()

    # Update settings
    # We need to patch the settings object or environment variables
    # Since settings are likely already loaded, we might need to reload or patch
    os.environ["DATABASE_URL"] = postgres.get_connection_url()
    os.environ["REDIS_URL"] = f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"
    
    # Re-create engine with new URL
    global engine, TestingSessionLocal
    engine.dispose()
    engine = create_engine(os.environ["DATABASE_URL"])
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Update settings object if possible, or rely on env vars if code reads them dynamically
    # Assuming settings reads from env vars, but might be cached.
    # For now, let's assume re-creating engine is enough for DB access in tests
    # But app code might use settings.DATABASE_URL
    settings.DATABASE_URL = os.environ["DATABASE_URL"]
    settings.REDIS_URL = os.environ["REDIS_URL"]

    yield

    postgres.stop()
    redis.stop()


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
    # command.downgrade(alembic_cfg, "base")
    # with engine.connect() as connection:
    #     connection.execute(text("DROP TYPE IF EXISTS ordersource CASCADE;"))
    #     connection.commit()
    
    # Dispose of the engine to close all connections
    engine.dispose()


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
    app.dependency_overrides[dependencies.get_db] = override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def anyio_backend():
    """Run async tests on asyncio only."""
    return "asyncio"


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


@pytest.fixture(scope="function")
def admin_headers(client: TestClient, test_admin_user: models.User) -> dict:
    """
    Returns headers with a valid admin access token.
    """
    from src.config import settings
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    r = client.post(f"{settings.API_V1_STR}/users/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    return {"Authorization": f"Bearer {a_token}"}


@pytest.fixture(scope="function")
def staged_sync_batch(db: Session, test_admin_user: models.User, test_product: Product) -> int:
    """
    Creates a staged sync batch with pending changes for testing.
    Returns the batch ID.
    """
    from src.models.pending_sync import SyncBatch, PendingSyncChange
    
    # Create a sync batch
    batch = SyncBatch(
        user_id=test_admin_user.id,
        source="google_sheets",
        status="pending",
        total_changes=2
    )
    db.add(batch)
    db.flush()
    
    # Add pending changes
    change1 = PendingSyncChange(
        batch_id=batch.id,
        entity="products",
        entity_id=test_product.id,
        entity_name=test_product.name,
        entity_sku=test_product.sku,
        field="cost_price",
        old_value="10.00",
        new_value="15.00",
        status="pending"
    )
    change2 = PendingSyncChange(
        batch_id=batch.id,
        entity="products",
        entity_id=test_product.id,
        entity_name=test_product.name,
        entity_sku=test_product.sku,
        field="default_resale_price",
        old_value="19.99",
        new_value="29.99",
        status="pending"
    )
    db.add(change1)
    db.add(change2)
    db.flush()
    
    return batch.id
