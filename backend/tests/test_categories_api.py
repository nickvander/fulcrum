"""End-to-end tests for the FP-07 category taxonomy.

Covers:
  - model/migration smoke (categories table + products.category_id exist)
  - public reads: flat list, single by slug (404), tree=true hierarchy,
    product_count, include_inactive
  - authed writes via JWT AND X-API-Key
  - slug auto-generation (accent strip) + uniqueness 409
  - 404s on update/delete of unknown id
  - delete nulls children's parent_id and products' category_id
  - GET /products?category_slug= filter (correct subset; unknown -> empty)
"""
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from src.models.api_key import ApiKey
from src.models.category import Category
from src.models.product import Product
from src.schemas.product import ProductCreate
from src.crud import crud_product


_BASE = "/api/v1/categories"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _api_key_headers(db: Session, user_id: int, raw_key: str) -> dict:
    db.add(
        ApiKey(
            user_id=user_id,
            name="cat test key",
            key_prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            is_active=True,
        )
    )
    db.flush()
    return {"X-API-Key": raw_key}


def _make_product(db: Session, name: str, sku: str, category_id=None) -> Product:
    p = crud_product.product.create(
        db,
        obj_in=ProductCreate(
            name=name, sku=sku, default_resale_price=10.0, cost_price=5.0
        ),
    )
    if category_id is not None:
        p.category_id = category_id
        db.add(p)
        db.flush()
    return p


# ---------------------------------------------------------------------------
# model / migration smoke
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_schema_has_categories_table_and_product_fk(db: Session):
    insp = sa_inspect(db.get_bind())
    assert "categories" in insp.get_table_names()
    product_cols = {c["name"] for c in insp.get_columns("products")}
    assert "category_id" in product_cols
    # legacy column kept
    assert "category" in product_cols


@pytest.mark.db
def test_category_self_ref_relationship(db: Session):
    parent = Category(name="Electrónica", slug="electronica")
    db.add(parent)
    db.flush()
    child = Category(name="Audio", slug="audio", parent_id=parent.id)
    db.add(child)
    db.flush()
    db.refresh(parent)
    assert [c.id for c in parent.children] == [child.id]
    assert child.parent.id == parent.id


# ---------------------------------------------------------------------------
# public reads
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_public_list_and_get_by_slug(client: TestClient, db: Session):
    cat = Category(name="Deportes", slug="deportes", sort_order=2)
    db.add(cat)
    db.flush()

    r = client.get(_BASE)  # no auth
    assert r.status_code == 200, r.text
    slugs = {c["slug"] for c in r.json()}
    assert "deportes" in slugs

    r = client.get(f"{_BASE}/deportes")
    assert r.status_code == 200
    assert r.json()["name"] == "Deportes"

    r = client.get(f"{_BASE}/does-not-exist")
    assert r.status_code == 404


@pytest.mark.db
def test_tree_returns_nested_children(client: TestClient, db: Session):
    parent = Category(name="Electrónica", slug="electronica", sort_order=0)
    db.add(parent)
    db.flush()
    db.add(Category(name="Audio", slug="audio", parent_id=parent.id, sort_order=0))
    db.add(
        Category(name="Cómputo", slug="computo", parent_id=parent.id, sort_order=1)
    )
    db.flush()

    r = client.get(_BASE, params={"tree": "true"})
    assert r.status_code == 200, r.text
    roots = {c["slug"]: c for c in r.json()}
    assert "electronica" in roots
    # Children only appear nested, not as roots
    assert "audio" not in roots
    child_slugs = [c["slug"] for c in roots["electronica"]["children"]]
    assert child_slugs == ["audio", "computo"]


@pytest.mark.db
def test_product_count_populated(client: TestClient, db: Session):
    cat = Category(name="Belleza", slug="belleza")
    db.add(cat)
    db.flush()
    _make_product(db, "Serum", "CAT-SERUM-1", category_id=cat.id)
    _make_product(db, "Crema", "CAT-CREMA-1", category_id=cat.id)

    r = client.get(f"{_BASE}/belleza")
    assert r.status_code == 200
    assert r.json()["product_count"] == 2


@pytest.mark.db
def test_include_inactive_flag(client: TestClient, db: Session):
    db.add(Category(name="Oculta", slug="oculta", is_active=False))
    db.flush()

    visible = {c["slug"] for c in client.get(_BASE).json()}
    assert "oculta" not in visible

    with_inactive = {
        c["slug"]
        for c in client.get(_BASE, params={"include_inactive": "true"}).json()
    }
    assert "oculta" in with_inactive


# ---------------------------------------------------------------------------
# authed writes (JWT + API key)
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_create_requires_auth(client: TestClient):
    r = client.post(_BASE, json={"name": "Nope"})
    assert r.status_code in (401, 403)


@pytest.mark.db
def test_create_with_jwt(client: TestClient, admin_headers: dict):
    r = client.post(_BASE, headers=admin_headers, json={"name": "Juguetes"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == "juguetes"
    assert body["name"] == "Juguetes"


@pytest.mark.db
def test_create_with_api_key(client: TestClient, db: Session, test_admin_user):
    headers = _api_key_headers(db, test_admin_user.id, "catkey00-" + "a" * 55)
    r = client.post(_BASE, headers=headers, json={"name": "Hogar y Cocina"})
    assert r.status_code == 200, r.text
    assert r.json()["slug"] == "hogar-y-cocina"


@pytest.mark.db
def test_slug_autogen_strips_accents(client: TestClient, admin_headers: dict):
    r = client.post(_BASE, headers=admin_headers, json={"name": "Electrónica"})
    assert r.status_code == 200, r.text
    assert r.json()["slug"] == "electronica"


@pytest.mark.db
def test_duplicate_slug_returns_409(client: TestClient, admin_headers: dict):
    r1 = client.post(
        _BASE, headers=admin_headers, json={"name": "Deportes", "slug": "deportes"}
    )
    assert r1.status_code == 200, r1.text
    r2 = client.post(
        _BASE, headers=admin_headers, json={"name": "Otro", "slug": "deportes"}
    )
    assert r2.status_code == 409


@pytest.mark.db
def test_autogen_slug_collision_gets_suffix(
    client: TestClient, db: Session, admin_headers: dict
):
    # Pre-existing 'deportes'
    db.add(Category(name="Deportes", slug="deportes"))
    db.flush()
    # Auto-gen from same name (no explicit slug) -> should not 409, gets -2
    r = client.post(_BASE, headers=admin_headers, json={"name": "Deportes"})
    assert r.status_code == 200, r.text
    assert r.json()["slug"] == "deportes-2"


@pytest.mark.db
def test_update_and_404(client: TestClient, db: Session, admin_headers: dict):
    cat = Category(name="Viejo", slug="viejo")
    db.add(cat)
    db.flush()
    cid = cat.id

    r = client.put(
        f"{_BASE}/{cid}", headers=admin_headers, json={"name": "Nuevo"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Nuevo"

    r = client.put(
        f"{_BASE}/999999", headers=admin_headers, json={"name": "X"}
    )
    assert r.status_code == 404


@pytest.mark.db
def test_delete_404(client: TestClient, admin_headers: dict):
    r = client.delete(f"{_BASE}/999999", headers=admin_headers)
    assert r.status_code == 404


@pytest.mark.db
def test_delete_nulls_children_and_products(
    client: TestClient, db: Session, admin_headers: dict
):
    parent = Category(name="Electrónica", slug="electronica")
    db.add(parent)
    db.flush()
    child = Category(name="Audio", slug="audio", parent_id=parent.id)
    db.add(child)
    db.flush()
    product = _make_product(db, "Bocina", "CAT-BOCINA-1", category_id=parent.id)
    parent_id = parent.id
    child_id = child.id
    product_id = product.id

    r = client.delete(f"{_BASE}/{parent_id}", headers=admin_headers)
    assert r.status_code == 200, r.text

    db.expire_all()
    assert db.get(Category, parent_id) is None
    # child survives, parent_id nulled
    refreshed_child = db.get(Category, child_id)
    assert refreshed_child is not None
    assert refreshed_child.parent_id is None
    # product survives, category_id nulled
    refreshed_product = db.get(Product, product_id)
    assert refreshed_product is not None
    assert refreshed_product.category_id is None


# ---------------------------------------------------------------------------
# products filter by category
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_products_filter_by_category_slug(client: TestClient, db: Session):
    cat_a = Category(name="Audio", slug="audio")
    cat_b = Category(name="Cómputo", slug="computo")
    db.add_all([cat_a, cat_b])
    db.flush()
    _make_product(db, "Audífonos", "FILT-AUD-1", category_id=cat_a.id)
    _make_product(db, "Bocina", "FILT-AUD-2", category_id=cat_a.id)
    _make_product(db, "Laptop", "FILT-COMP-1", category_id=cat_b.id)
    _make_product(db, "Sin categoría", "FILT-NONE-1")
    db.flush()

    r = client.get("/api/v1/products", params={"category_slug": "audio"})
    assert r.status_code == 200, r.text
    names = {p["name"] for p in r.json()["data"]}
    assert names == {"Audífonos", "Bocina"}


@pytest.mark.db
def test_products_filter_unknown_slug_returns_empty(client: TestClient, db: Session):
    _make_product(db, "Algo", "FILT-X-1")
    db.flush()
    r = client.get("/api/v1/products", params={"category_slug": "no-existe"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"] == []
    assert body["totalItems"] == 0


@pytest.mark.db
def test_products_filter_by_category_id(client: TestClient, db: Session):
    cat = Category(name="Deportes", slug="deportes")
    db.add(cat)
    db.flush()
    _make_product(db, "Pelota", "FILT-ID-1", category_id=cat.id)
    _make_product(db, "Otra cosa", "FILT-ID-2")
    db.flush()

    r = client.get("/api/v1/products", params={"category_id": cat.id})
    assert r.status_code == 200, r.text
    names = {p["name"] for p in r.json()["data"]}
    assert names == {"Pelota"}
