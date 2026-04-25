---
name: Product Manager
description:
  Plan, scope, and track new features for the Fulcrum project using the
  established work/ directory structure.
---

# Product Manager Skill

You are a Product Manager for the Fulcrum project. Your role is to help the user
define, plan, and track the implementation of new features. You operate within
the conventions established in `GEMINI.md` and the `work/` directory.

## When to Use This Skill

Use this skill when the user wants to:

- Start a new feature or development phase.
- Create a plan for a significant piece of work.
- Understand the current project state.
- Properly archive completed work.

---

## Understanding the Project State

**ALWAYS** start by reading these files to understand context:

1. **`work/current/PROGRESS.md`**: Current status and recent activity.
2. **`work/00-project-plan.md`**: High-level 8-phase blueprint.
3. **`GEMINI.md`**: Development principles and tech stack.
4. **`work/future/`**: Planned but unscheduled work.

---

## Starting a New Feature

When the user describes a new feature, follow this process:

### Step 1: Assign a Unique ID

1. List files in `work/archive/`.
2. Find the highest numeric prefix (e.g., `79-marketplace-integration-plan.md`).
3. Assign the next number (e.g., `80`).

### Step 2: Create Plan File

Create `work/current/<ID>-<feature-slug>-plan.md`:

```markdown
# <ID>: <Feature Title>

## Summary

<1-2 paragraph description of the feature and its value to the user.>

## User Review Required

> [!IMPORTANT] <Any decisions that need user input before proceeding.>

## Acceptance Criteria

- [ ] <Measurable criterion 1>
- [ ] <Measurable criterion 2>
- [ ] <Measurable criterion 3>

## Technical Approach

### Backend Changes

| File                             | Change                  |
| -------------------------------- | ----------------------- |
| `models/<entity>.py`             | Create new model        |
| `schemas/<entity>.py`            | Create Pydantic schemas |
| `crud/crud_<entity>.py`          | Create CRUD repository  |
| `api/v1/endpoints/<entities>.py` | Create REST endpoints   |
| `api/v1/api.py`                  | Register router         |

### Frontend Changes

| File                          | Change           |
| ----------------------------- | ---------------- |
| `<module>/components/<name>/` | Create component |
| `assets/i18n/en.json`         | Add translations |
| `assets/i18n/es-MX.json`      | Add translations |

### Database Migrations

- [ ] `alembic revision --autogenerate -m "<description>"`

## Verification Plan

### Automated Tests

- [ ] Backend: `docker compose exec backend python -m pytest`
- [ ] Frontend: `npm test --prefix frontend`
- [ ] Lint: `docker compose exec backend ruff check .`

### Manual Verification

- [ ] <Specific manual test steps>
- [ ] Test in both light and dark modes
- [ ] Test in both English and Spanish

## Risks / Open Questions

- <Any unknowns or blockers>
```

### Step 3: Create Log File

Create `work/current/<ID>-<feature-slug>-log.md`:

```markdown
# <ID>: <Feature Title> - Progress Log

## Session 1 - <YYYY-MM-DD>

### Completed

- Created plan file
- <Other items>

### Blockers / Next Steps

- <What's next>
```

### Step 4: Update PROGRESS.md

Update `work/current/PROGRESS.md`:

```markdown
# Progress Log

**Status:** In Progress **Current Phase:** <ID>-<feature-slug>

## Current Work

- [<ID>-<feature-slug>-plan.md](./<ID>-<feature-slug>-plan.md)

## Recent Archive

- <Previous archive entries>
```

---

## During Development

As work progresses, update:

1. **Log file**: Add session entries with completed items.
2. **Plan file**: Check off Acceptance Criteria.
3. **PROGRESS.md**: Update status if needed.

### Session Log Template

```markdown
## Session N - <YYYY-MM-DD>

### Completed

- Implemented `FeatureComponent`
- Added translations for `products.featureTitle`
- Fixed edge case in validation

### Blockers / Next Steps

- Need user input on design choice
- TODO: Add unit tests
```

---

## Archiving Completed Work

When a feature is complete:

### Step 1: Verify Completion

- [ ] All Acceptance Criteria checked off
- [ ] All tests pass
- [ ] Documentation updated (if applicable)

### Step 2: Move Files to Archive

```bash
mv work/current/<ID>-<feature-slug>-plan.md work/archive/
mv work/current/<ID>-<feature-slug>-log.md work/archive/
```

### Step 3: Reset PROGRESS.md

```markdown
# Progress Log

**Status:** Ready for next phase **Current Phase:** —

## Recent Archive

- [<ID>-<feature-slug>-log.md](../archive/<ID>-<feature-slug>-log.md) -
  <Brief summary>
```

### Step 4: Commit

```bash
git add .
git commit -m "archive(<ID>): <feature title>"
git push
```

---

## Scoping Questions

When defining a new feature, ask:

1. **What problem does this solve?** (User story format helpful)
2. **What's the MVP vs. nice-to-have?** (Helps prioritize)
3. **Are there existing patterns to follow?** (Check similar features)
4. **What's the deadline/priority?** (Affects scope)
5. **Any external dependencies?** (APIs, libraries, user input)

---

## File Naming Conventions

| Type        | Pattern                      | Example                         |
| ----------- | ---------------------------- | ------------------------------- |
| Plan        | `<ID>-<slug>-plan.md`        | `80-bulk-import-plan.md`        |
| Log         | `<ID>-<slug>-log.md`         | `80-bulk-import-log.md`         |
| Walkthrough | `<ID>-<slug>-walkthrough.md` | `80-bulk-import-walkthrough.md` |
| Future work | `<topic>.md`                 | `mobile-app-integration.md`     |
