---
name: Backend Feature Development
description: Implement backend features from database model to API endpoint, following Fulcrum's Repository Pattern.
---

# Backend Feature Development Skill

You are a backend developer for the Fulcrum project. Your role is to implement
new features following the project's Repository Pattern and coding conventions.

## When to Use This Skill

Use this skill when the user wants to:
- Add a new database model.
- Create new API endpoints.
- Implement business logic in the service layer.
- Extend existing models with new fields.

---

## Architecture Overview

```
backend/src/
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
├── crud/            # Repository layer (database operations)
├── services/        # Business logic layer (AI, integrations)
├── api/v1/endpoints/  # FastAPI route handlers
├── api/v1/api.py    # Centralized router registration
└── api/dependencies.py  # Shared dependencies (get_db, etc.)
```

**Flow**: `API Endpoint → Service (optional) → CRUD Repository → Model`

---

## Step 1: Create the Model

File: `backend/src/models/<entity>.py`

```python
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base


class EntityName(Base):
    __tablename__ = "entity_names"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Timestamps (use func.now() for server default)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="entity_names")
```

**Register in `backend/src/models/__init__.py`:**

```python
from .entity import EntityName  # noqa: F401
```

---

## Step 2: Create Pydantic Schemas

File: `backend/src/schemas/<entity>.py`

**Pattern**: `Base` → `Create` → `Update` → `InDBBase` → `Response`

```python
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class EntityNameBase(BaseModel):
    """Shared properties - fields common to create/update/response."""
    name: str
    description: Optional[str] = None
    amount: Optional[float] = None
    is_active: Optional[bool] = True
    user_id: Optional[int] = None
    supplier_id: Optional[int] = None


class EntityNameCreate(EntityNameBase):
    """Properties for creation (POST body). Add required fields here."""
    pass


class EntityNameUpdate(BaseModel):
    """Properties for update (PUT/PATCH body). ALL fields optional."""
    name: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    is_active: Optional[bool] = None
    user_id: Optional[int] = None
    supplier_id: Optional[int] = None


class EntityNameInDBBase(EntityNameBase):
    """Properties shared by models stored in DB."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntityName(EntityNameInDBBase):
    """Properties to return to client (response model)."""
    pass


# Optional: Summary/Aggregate schemas
class EntityNameSummary(BaseModel):
    """Aggregated data for dashboards."""
    total_count: int
    total_amount: float
    by_category: dict[str, float]
```

**Register in `backend/src/schemas/__init__.py`:**

```python
from .entity import EntityName, EntityNameCreate, EntityNameUpdate  # noqa: F401
```

---

## Step 3: Create CRUD Repository

File: `backend/src/crud/crud_<entity>.py`

```python
from typing import Optional
from sqlalchemy.orm import Session

from src.crud.base import CRUDBase
from src.models.entity import EntityName
from src.schemas.entity import EntityNameCreate, EntityNameUpdate


class CRUDEntityName(CRUDBase[EntityName, EntityNameCreate, EntityNameUpdate]):
    """Repository for EntityName operations."""

    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[EntityName]:
        """Get all entities belonging to a user."""
        return (
            db.query(self.model)
            .filter(EntityName.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_supplier(
        self, db: Session, *, supplier_id: int
    ) -> list[EntityName]:
        """Get all entities for a supplier."""
        return (
            db.query(self.model)
            .filter(EntityName.supplier_id == supplier_id)
            .all()
        )

    def get_active(self, db: Session) -> list[EntityName]:
        """Get only active entities."""
        return db.query(self.model).filter(EntityName.is_active == True).all()


# Singleton instance
entity_name = CRUDEntityName(EntityName)
```

**Register in `backend/src/crud/__init__.py`:**

```python
from .crud_entity import entity_name  # noqa: F401
```

---

## Step 4: Create API Endpoints

File: `backend/src/api/v1/endpoints/<entities>.py`

```python
from typing import Any, List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.crud import crud_entity
from src.models.entity import EntityName as EntityModel
from src.schemas import entity as entity_schema
from src.api.dependencies import get_db

router = APIRouter()


@router.get("/", response_model=List[entity_schema.EntityName])
def read_entities(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
) -> Any:
    """
    Retrieve entities with optional filters.
    """
    query = db.query(EntityModel)

    if user_id is not None:
        query = query.filter(EntityModel.user_id == user_id)
    if is_active is not None:
        query = query.filter(EntityModel.is_active == is_active)

    return query.order_by(EntityModel.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=entity_schema.EntityName)
def create_entity(
    *,
    db: Session = Depends(get_db),
    entity_in: entity_schema.EntityNameCreate,
) -> Any:
    """
    Create new entity.
    """
    return crud_entity.entity_name.create(db, obj_in=entity_in)


@router.get("/{id}", response_model=entity_schema.EntityName)
def read_entity(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Get entity by ID.
    """
    entity = crud_entity.entity_name.get(db, id=id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.put("/{id}", response_model=entity_schema.EntityName)
def update_entity(
    *,
    db: Session = Depends(get_db),
    id: int,
    entity_in: entity_schema.EntityNameUpdate,
) -> Any:
    """
    Update an entity.
    """
    entity = crud_entity.entity_name.get(db, id=id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return crud_entity.entity_name.update(db, db_obj=entity, obj_in=entity_in)


@router.delete("/{id}", response_model=entity_schema.EntityName)
def delete_entity(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Delete an entity.
    """
    entity = crud_entity.entity_name.get(db, id=id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return crud_entity.entity_name.remove(db, id=id)
```

---

## Step 5: Register Router

File: `backend/src/api/v1/api.py`

Add to the existing file:

```python
from src.api.v1.endpoints import entities

api_router.include_router(
    entities.router,
    prefix="/entities",
    tags=["entities"],
)
```

---

## Step 6: Create Database Migration

```bash
docker compose exec backend alembic revision --autogenerate -m "add entity_names table"
```

**ALWAYS review the generated migration file**, then apply:

```bash
docker compose exec backend alembic upgrade head
```

---

## Step 7: Write Tests

File: `backend/tests/api/v1/test_<entities>.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.entity import EntityName


@pytest.fixture
def sample_entity(db: Session) -> EntityName:
    """Create a sample entity for testing."""
    entity = EntityName(name="Test Entity", description="A test entity", amount=100.0)
    db.add(entity)
    db.commit()
    db.refresh(entity)
    yield entity
    # Cleanup
    db.delete(entity)
    db.commit()


def test_create_entity(client: TestClient, db: Session):
    response = client.post(
        "/api/v1/entities/",
        json={"name": "New Entity", "description": "Description", "amount": 50.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Entity"
    assert data["amount"] == 50.0
    assert "id" in data


def test_read_entity(client: TestClient, sample_entity: EntityName):
    response = client.get(f"/api/v1/entities/{sample_entity.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_entity.id
    assert data["name"] == sample_entity.name


def test_read_entity_not_found(client: TestClient):
    response = client.get("/api/v1/entities/99999")
    assert response.status_code == 404


def test_update_entity(client: TestClient, sample_entity: EntityName):
    response = client.put(
        f"/api/v1/entities/{sample_entity.id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_delete_entity(client: TestClient, sample_entity: EntityName, db: Session):
    response = client.delete(f"/api/v1/entities/{sample_entity.id}")
    assert response.status_code == 200
    # Verify deleted
    assert db.query(EntityName).filter(EntityName.id == sample_entity.id).first() is None
```

---

## Verification Checklist

- [ ] Model registered in `models/__init__.py`
- [ ] Schemas registered in `schemas/__init__.py`
- [ ] CRUD registered in `crud/__init__.py`
- [ ] Router registered in `api/v1/api.py`
- [ ] Migration created: `alembic revision --autogenerate`
- [ ] Migration applied: `alembic upgrade head`
- [ ] Tests written and passing
- [ ] Linter passes: `docker compose exec backend ruff check .`
- [ ] All tests pass: `docker compose exec backend python -m pytest`
