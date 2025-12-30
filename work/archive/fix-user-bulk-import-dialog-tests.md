# Fix User Bulk Import Dialog Tests

## Status: Future Work

**Priority:** Medium  
**Complexity:** High  
**Estimated Effort:** 8-16 hours

## Problem Summary

The `UserBulkImportDialogComponent` test suite is currently disabled with
`xdescribe` because it causes the entire test runner to hang for 120+ seconds in
CI/CD. This is a critical test gap that needs to be properly fixed.

## Root Cause

The component's template contains Material components (MatTabs, MatTable with
dataSource binding) that create uncompleted observables during initialization in
the test environment. The timeout occurs in the `beforeEach` block during
`fixture.detectChanges()`, before any individual tests run.

This is the same pattern seen in ProductForm tests (documented in
`work/PROGRESS.md`). Complex Material component templates with data-bound
elements create async operations that don't properly complete in the test
environment, causing the test runner to wait indefinitely for Zone.js to
stabilize.

## Failed Approaches

The following fixes were all attempted but failed to resolve the timeout:

1. **fakeAsync/tick pattern** - FAILED
2. **async/await with fixture.whenStable()** - FAILED
3. **takeUntil pattern in component with OnDestroy** - FAILED
4. **afterEach fixture.destroy()** - FAILED
5. **Simplified test (no async assertions)** - FAILED
6. **Disabling individual test with xit()** - FAILED

## Proper Solution Approaches

To properly fix this issue (not just disable the tests), consider the following
approaches:

### 1. Mock Material Components

**Approach:** Replace the complex Material components with simple mocks in the
test environment.

**Implementation:**

```typescript
// Create mock components
@Component({
  selector: "mat-tab-group",
  template: "<ng-content></ng-content>",
  standalone: true,
})
class MockMatTabGroup {}

@Component({
  selector: "mat-tab",
  template: "<ng-content></ng-content>",
  standalone: true,
  inputs: ["label"],
})
class MockMatTab {}

// Use in test configuration
TestBed.configureTestingModule({
  imports: [UserBulkImportDialogComponent],
  providers: [
    /* ... */
  ],
}).overrideComponent(UserBulkImportDialogComponent, {
  remove: { imports: [MatTabsModule, MatTableModule] },
  add: { imports: [MockMatTabGroup, MockMatTab /* ... */] },
});
```

**Pros:**

- Eliminates the source of uncompleted observables
- Tests run quickly without Material component overhead
- Component logic is still tested

**Cons:**

- Doesn't test actual Material component integration
- Requires maintaining mock components
- Template changes may require mock updates

### 2. Refactor Component to Separate Data from Presentation

**Approach:** Extract the data/logic layer from the presentation layer, test
them separately.

**Implementation:**

```typescript
// Create a service to handle bulk import logic
@Injectable()
export class BulkImportService {
  constructor(private userService: UserService) {}

  processFile(file: File): Observable<ImportResult> {
    return this.userService.bulkImportUsers(file);
  }
}

// Simplify component to be mostly presentational
export class UserBulkImportDialogComponent {
  constructor(
    private bulkImportService: BulkImportService,
    // ...
  ) {}

  upload(): void {
    this.bulkImportService
      .processFile(this.selectedFile)
      .pipe(takeUntil(this.destroy$))
      .subscribe(/* ... */);
  }
}
```

Then create separate test files:

- `bulk-import.service.spec.ts` - Test the logic without UI
- `user-bulk-import-dialog.spec.ts` - Light integration test with mocked service

**Pros:**

- Better separation of concerns
- Logic tests run fast and reliably
- Follows Angular best practices
- Easier to maintain and extend

**Cons:**

- Requires refactoring the component
- More files to maintain

### 3. Use NO_ERRORS_SCHEMA and Shallow Testing

**Approach:** Test the component in isolation without rendering child
components.

**Implementation:**

```typescript
import { NO_ERRORS_SCHEMA } from "@angular/core";

TestBed.configureTestingModule({
  imports: [UserBulkImportDialogComponent],
  schemas: [NO_ERRORS_SCHEMA],
  providers: [
    /* ... */
  ],
});
```

**Pros:**

- Quick fix, minimal code changes
- Component logic is still tested
- No Material component rendering issues

**Cons:**

- Doesn't test template integration
- Can hide real template errors
- Not recommended for components with complex templates

### 4. Increase Test Timeout and Add Retry Logic

**Approach:** Configure Web Test Runner to wait longer and retry failed tests.

**Implementation:** In `web-test-runner.config.mjs`:

```javascript
export default {
  testsFinishTimeout: 300000, // 5 minutes
  testFramework: {
    config: {
      timeout: 60000, // 1 minute per test
      retries: 2,
    },
  },
};
```

**Pros:**

- No code changes needed
- May work if issue is just slow initialization

**Cons:**

- Doesn't fix the root cause
- Slow CI/CD pipelines
- May still fail intermittently
- **NOT RECOMMENDED** as a standalone solution

## Recommended Solution

**Use Approach #2 (Refactor with Service Layer)** for the following reasons:

1. **Long-term maintainability**: Better architecture that's easier to test and
   extend
2. **Comprehensive testing**: Can test logic thoroughly in fast unit tests
3. **Best practices**: Aligns with Angular's recommended patterns
4. **Reusability**: Service can be used by other components if needed
5. **Performance**: Fast, reliable tests without timeout issues

Combine with Approach #1 (Mock Material Components) for the presentation layer
tests to ensure the UI integration works without timeout issues.

## Implementation Steps

1. **Create `BulkImportService`:**
   - Extract all bulk import logic from the component
   - Handle file validation, API calls, error handling
   - Return observables for async operations

2. **Update `UserBulkImportDialogComponent`:**
   - Inject and use `BulkImportService`
   - Keep only presentation logic (UI state, user interactions)
   - Maintain existing template and functionality

3. **Create service tests (`bulk-import.service.spec.ts`):**
   - Test file validation
   - Test API call with mocked UserService
   - Test error handling
   - Test result processing

4. **Update component tests (`user-bulk-import-dialog.spec.ts`):**
   - Mock `BulkImportService` instead of `UserService`
   - Consider using mock Material components
   - Test UI interactions and state changes
   - Re-enable with `describe` instead of `xdescribe`

5. **Verify locally:**
   - Run `npm test --prefix frontend`
   - Confirm all tests pass without timeouts
   - Verify test coverage is maintained or improved

6. **Verify in CI/CD:**
   - Push changes and monitor CI pipeline
   - Confirm tests pass in CI environment
   - Check total test execution time

## Success Criteria

- [ ] All `UserBulkImportDialogComponent` tests enabled and passing
- [ ] No test timeouts in local or CI/CD environments
- [ ] Test execution time < 5 seconds for the component tests
- [ ] Test coverage maintained or improved (aim for >80%)
- [ ] Component functionality unchanged (works in production)
- [ ] Architecture improvements documented

## Related Issues

- ProductForm test hangs (see `work/PROGRESS.md` - multiple sessions)
- Material component testing challenges in Angular test environment
- Zone.js stabilization issues with complex component templates

## References

- Current disabled tests:
  `frontend/src/app/users/components/user-bulk-import-dialog/user-bulk-import-dialog.spec.ts`
- Component source:
  `frontend/src/app/users/components/user-bulk-import-dialog/user-bulk-import-dialog.ts`
- Similar pattern documentation: `work/PROGRESS.md` (search for "ProductForm
  test hanging")
