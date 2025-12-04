# Missing Items for Bazel Implementation

## Phase 1: Foundation ✅ COMPLETE
- [x] Install Bazel and dependencies
- [x] Create .bazelversion, .bazelrc, .bazelignore
- [x] Create MODULE.bazel with Bzlmod configuration
- [x] Configure rules_python with Python 3.11
- [x] Configure aspect_rules_js for frontend
- [x] Configure rules_oci for Docker builds
- [x] Configure rules_pkg for packaging

## Phase 2: Backend Python ✅ COMPLETE
- [x] Generate requirements_lock.txt with pip-compile
- [x] Create backend/BUILD.bazel
- [x] Create backend/src/BUILD.bazel with py_library and py_binary
- [x] Build //backend/src:main successfully
- [x] Build //backend/src:celery_worker successfully

## Phase 3: Backend Testing ✅ PARTIAL
- [x] Create backend/tests/BUILD.bazel
- [x] Configure py_test rules for 9 test modules
- [x] Successfully run test_fast_dummy
- [ ] Configure test environment variables
- [ ] Set up PostgreSQL test container with Bazel
- [ ] Set up Redis test container with Bazel
- [ ] Make all backend tests pass with Bazel

## Phase 4: Frontend Dependencies ✅ COMPLETE
- [x] Install pnpm
- [x] Generate frontend/pnpm-lock.yaml
- [x] Configure npm extension in MODULE.bazel
- [x] Create frontend/BUILD.bazel
- [x] Verify dependency resolution

## Phase 5: Frontend Build 🚧 NOT STARTED
- [ ] Research Angular + aspect_rules_js integration
- [ ] Create ts_project rules for TypeScript compilation
- [ ] Configure Angular build target
- [ ] Set up development build target
- [ ] Set up production build target
- [ ] Configure asset handling
- [ ] Build PWA successfully

## Phase 6: Frontend Testing 🚧 NOT STARTED
- [ ] Integrate Web Test Runner with Bazel
- [ ] Configure Playwright for headless testing
- [ ] Create test rules for spec files
- [ ] Make all frontend tests pass with Bazel

## Phase 7: Docker Integration ✅ PARTIAL

### Backend Container ✅ COMPLETE
- [x] Add OCI base image pulls to MODULE.bazel (python:3.11-slim)
- [x] Create backend/image/BUILD.bazel
- [x] Configure pkg_tar for backend application
- [x] Configure oci_image for backend
- [x] Configure oci_load for Docker export
- [x] Test backend container build
- [x] Verify backend container loads into Docker
- [x] Add visibility to py_binary targets
- [x] Run bazel mod tidy

### Frontend Container 🚧 NOT STARTED
- [ ] Create frontend/image/BUILD.bazel
- [ ] Configure nginx.conf
- [ ] Package Angular build output
- [ ] Configure oci_image for frontend
- [ ] Configure oci_load for Docker export
- [ ] Test frontend container build

### Test Containers 🚧 NOT STARTED
- [ ] Configure PostgreSQL test container with pgvector
- [ ] Configure Redis test container
- [ ] Wire test containers to py_test rules
- [ ] Verify all backend tests pass with containers

### Docker Compose Integration ✅ COMPLETE
- [x] Create docker-compose.bazel.yml example
- [x] Document how to use Bazel vs traditional docker-compose
- [x] Maintain backward compatibility

## Phase 8: CI/CD Integration 🚧 NOT STARTED

### GitHub Actions Updates
- [ ] Update .github/workflows/backend-tests.yml
  - [ ] Install Bazel (or use bazelisk)
  - [ ] Replace pytest with bazel test
  - [ ] Configure environment for Docker containers
- [ ] Update .github/workflows/frontend-tests.yml
  - [ ] Replace Web Test Runner with bazel test
- [ ] Update .github/workflows/e2e-tests.yml (if needed)
- [ ] Create .github/workflows/bazel-build.yml for general builds

### Performance Optimization
- [ ] Research remote caching options (GitHub cache, Bazel Remote Cache)
- [ ] Configure remote cache in .bazelrc
- [ ] Add `build:ci` configuration
- [ ] Implement test sharding for parallel execution
- [ ] Measure and document build time improvements

## Phase 9: Documentation 🚧 NOT STARTED

### README.md
- [ ] Add Bazel installation instructions
- [ ] Add "Building with Bazel" section
- [ ] Update Quick Start to include Bazel commands
- [ ] Add performance comparison table

### CONTRIBUTING.md
- [ ] Add Bazel development workflow guide
- [ ] Document how to add new dependencies
- [ ] Document how to add new BUILD files
- [ ] Add coding standards for BUILD files
- [ ] Explain when to use Bazel vs Docker Compose

### /docs Directory
- [x] Create docs/guides/using-bazel.md
- [ ] Update architecture documentation
- [ ] Add Mermaid diagram showing Bazel + Docker flow
- [ ] Create troubleshooting guide for common Bazel issues
- [ ] Document remote caching setup

### Quick Reference
- [x] Create BAZEL_QUICKSTART.md

## Phase 10: Verification & Validation 🚧 NOT STARTED

### Build Verification
- [ ] `bazel build //...` completes successfully
- [ ] Backend binary runs correctly
- [ ] Celery worker runs correctly
- [ ] Frontend serves correctly in development
- [ ] Frontend builds correctly for production

### Test Verification
- [ ] All backend unit tests pass
- [ ] All backend integration tests pass
- [ ] All frontend unit tests pass
- [ ] E2E tests pass with Bazel-built images

### Container Verification
- [x] Backend Docker image builds
- [x] Backend container loads into Docker
- [ ] Backend container starts successfully and serves requests
- [ ] Frontend Docker image builds
- [ ] Frontend container serves correctly
- [ ] All containers work together in docker-compose

### CI/CD Verification
- [ ] Backend tests workflow passes
- [ ] Frontend tests workflow passes
- [ ] E2E tests workflow passes
- [ ] Build times meet 30% improvement goal

### Performance Benchmarks
- [ ] Measure clean build time
- [ ] Measure incremental build time
- [ ] Measure test execution time
- [ ] Measure CI/CD pipeline time
- [ ] Document all measurements

## Blockers / Open Questions

1. **Angular Build Strategy**: Need to decide between:
   - Using Angular CLI via Bazel (simpler, less control)
   - Direct TypeScript compilation (more complex, more control)
   
2. **Test Container Management**: How to best integrate Docker test containers with Bazel's hermetic build?

3. **Remote Caching**: Which solution to use?
   - GitHub Actions cache (free, simpler)
   - Bazel Remote Cache (better performance, more setup)
   - Cloud provider (GCS, S3)

4. **Development Workflow**: Should Bazel replace docker-compose for local dev, or complement it?

## Success Metrics

- [ ] All builds 100% reproducible
- [ ] Incremental builds 30%+ faster
- [ ] All tests passing with Bazel
- [ ] CI/CD using Bazel exclusively
- [ ] Team comfortable with Bazel workflows
- [ ] Documentation complete and accurate
