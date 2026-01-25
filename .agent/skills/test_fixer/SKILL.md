---
name: Test Fixer
description: Debug and fix common test failures in Fulcrum's backend (pytest) and frontend (Web Test Runner + Playwright) test suites.
---

# Test Fixer Skill

You are a QA engineer for the Fulcrum project. Your role is to diagnose and fix
test failures in both backend and frontend test suites.

## When to Use This Skill

Use this skill when:
- Tests are failing and blocking commits.
- Pre-commit hooks are failing on test steps.
- Debugging flaky or hanging tests.

---

## Backend Test Debugging (pytest)

### Running Tests

```bash
# All tests
docker compose exec backend python -m pytest

# Specific file
docker compose exec backend python -m pytest tests/api/v1/test_products.py

# Specific test
docker compose exec backend python -m pytest tests/api/v1/test_products.py::test_create_product -v

# Stop on first failure
docker compose exec backend python -m pytest -x

# With output
docker compose exec backend python -m pytest -v -s
```

### Common Issues

#### Issue: `relation "table" does not exist`

**Cause**: Database schema out of sync.

**Solution**:
```bash
docker compose down -v
docker compose up -d
docker compose exec backend alembic upgrade head
```

See `database_migration` skill for details.

---

#### Issue: `IntegrityError: duplicate key`

**Cause**: Test data conflicts with fixtures.

**Solutions**:
1. Use unique values (UUIDs, timestamps).
2. Add cleanup in fixtures:
   ```python
   @pytest.fixture
   def sample_entity(db: Session):
       entity = EntityName(name="Test")
       db.add(entity)
       db.commit()
       yield entity
       db.delete(entity)
       db.commit()
   ```

---

#### Issue: `ForeignKeyViolation`

**Cause**: Deleting/modifying a record with dependencies.

**Solutions**:
1. Create fixtures in dependency order.
2. Delete in reverse order.
3. Use `cascade="all, delete-orphan"` in relationships.

---

#### Issue: Test passes alone, fails in suite

**Cause**: Shared state between tests.

**Solution**: Ensure transaction isolation:
```python
@pytest.fixture
def db(db_session):
    yield db_session
    db_session.rollback()
```

---

## Frontend Test Debugging (Web Test Runner)

### Running Tests

```bash
# All tests
npm test --prefix frontend

# Watch mode
npm test --prefix frontend -- --watch

# Specific file (pattern match)
npm test --prefix frontend -- --files "**/product-list/**/*.spec.ts"
```

### Common Issues

#### Issue: `NullInjectorError: No provider for X`

**Cause**: Missing dependency in test module.

**Solution**:
```typescript
await TestBed.configureTestingModule({
  imports: [
    ComponentUnderTest,
    NoopAnimationsModule,
    getTranslocoModule(),  // REQUIRED for any translated component
    HttpClientTestingModule,
  ],
  providers: [
    { provide: SomeService, useValue: mockService },
    { provide: MAT_DIALOG_DATA, useValue: {} },
    { provide: MatDialogRef, useValue: { close: () => {} } },
  ],
}).compileComponents();
```

---

#### Issue: Tests hang / timeout

**Cause**: Unresolved observables or pending HTTP.

**Solutions**:

1. **Use `fakeAsync` + `tick`:**
   ```typescript
   import { fakeAsync, tick, flush } from '@angular/core/testing';

   it('should work', fakeAsync(() => {
     component.loadData();
     tick(500);
     flush();
     expect(component.data).toBeDefined();
   }));
   ```

2. **Mock HTTP responses:**
   ```typescript
   const httpMock = TestBed.inject(HttpTestingController);
   component.loadData();
   const req = httpMock.expectOne('/api/v1/data');
   req.flush({ items: [] });
   ```

3. **Use `done` callback:**
   ```typescript
   it('should work', (done) => {
     component.data$.subscribe(data => {
       expect(data).toBeDefined();
       done();
     });
   });
   ```

---

#### Issue: Translation keys showing instead of text

**Cause**: Transloco not configured.

**Solution**: Use the testing module:
```typescript
import { getTranslocoModule } from '../../../testing/transloco-testing.module';

TestBed.configureTestingModule({
  imports: [getTranslocoModule()],
});
```

---

#### Issue: Dialog tests failing

**Cause**: `MAT_DIALOG_DATA` not provided.

**Solution**:
```typescript
TestBed.configureTestingModule({
  imports: [DialogComponent],
  providers: [
    { provide: MAT_DIALOG_DATA, useValue: { itemId: 1 } },
    { provide: MatDialogRef, useValue: { close: () => {} } },
  ],
});
```

---

#### Issue: `sinon` not defined

**Cause**: Missing import.

**Solution**:
```typescript
import sinon from 'sinon';

const spy = sinon.spy(service, 'method');
expect(spy.calledOnce).to.be.true;
```

---

## Debugging Steps

### 1. Reproduce Locally

```bash
# Backend
docker compose exec backend python -m pytest path/to/test.py -v

# Frontend
npm test --prefix frontend -- --files "path/to/test.spec.ts"
```

### 2. Isolate the Failure

- Run failing test alone.
- If passes alone → shared state issue.
- If fails alone → inspect test setup.

### 3. Add Debugging

**Backend:**
```python
def test_something(db):
    print(f"DB state: {db.query(Model).count()}")
    # ... test ...
```

**Frontend:**
```typescript
it('should work', () => {
  console.log('Component:', component);
  fixture.detectChanges();
  console.log('After detectChanges:', component.data);
});
```

### 4. Check Fixtures

- Verify fixtures create expected state.
- Check for cleanup after each test.

---

## Pre-Commit Hook Failures

If pre-commit hooks fail:

1. **Identify which check failed**: Read the error output.
2. **Fix the specific issue**:
   - Lint errors: `docker compose exec backend ruff check --fix .`
   - Test failures: Debug using steps above.
   - Type errors: Check imports and types.

3. **Re-run hooks**:
   ```bash
   git add .
   git commit -m "message"
   ```

---

## Verification

After fixing:

1. ✅ Run the specific test: Confirm it passes.
2. ✅ Run the full suite: Confirm no regressions.
3. ✅ Run pre-commit hooks: Confirm commit succeeds.
