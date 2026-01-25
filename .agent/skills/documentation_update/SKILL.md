---
name: Documentation Update
description: Maintain Fulcrum's documentation hub in /docs and update progress tracking files.
---

# Documentation Update Skill

You are a technical writer for the Fulcrum project. Your role is to maintain the
single source of truth for project documentation.

## When to Use This Skill

Use this skill when:
- Adding documentation for a new feature.
- Updating existing guides after changes.
- Managing progress logs in `work/`.
- Updating `GEMINI.md` or `README.md`.

---

## Documentation Structure

```
docs/
├── source/
│   ├── getting-started/    # Setup guides (backend, frontend, dev environment)
│   ├── guides/             # How-to documents (Google Sheets, deployment)
│   ├── explanation/        # Architecture deep-dives (AI agents, marketplace)
│   └── reference/          # API specs, config reference
└── conf.py                 # Sphinx configuration

work/
├── 00-project-plan.md      # High-level 8-phase blueprint
├── current/                # Active work (PROGRESS.md, plan files)
├── future/                 # Planned but unscheduled work
└── archive/                # Completed work (95+ archived plans/logs)
```

---

## Adding Documentation

### Step 1: Determine Location

| Content Type | Directory |
|-------------|-----------|
| Initial setup, installation | `docs/source/getting-started/` |
| Step-by-step how-tos | `docs/source/guides/` |
| Architecture, design decisions | `docs/source/explanation/` |
| API specs, configuration | `docs/source/reference/` |

### Step 2: Create the File

For RST files:
```rst
<Topic Title>
=============

Introduction paragraph.

Section 1
---------

Content...
```

For Markdown files (user guides):
```markdown
# Topic Title

Introduction paragraph.

## Section 1

Content...
```

### Step 3: Add to Index

Update `docs/source/<directory>/index.rst`:
```rst
.. toctree::
   :maxdepth: 2

   existing-doc
   new-topic        <-- Add this
```

### Step 4: Build and Verify

```bash
cd docs
make html
# Open _build/html/index.html
```

---

## Updating Progress Files

### work/current/PROGRESS.md

**Format:**
```markdown
# Progress Log

**Status:** In Progress | Ready for next phase
**Current Phase:** <ID>-<feature-slug> | —

## Current Work

- [<ID>-<feature-slug>-plan.md](./<ID>-<feature-slug>-plan.md)

## Recent Archive

- [<ID>-<slug>-log.md](../archive/<ID>-<slug>-log.md) - Brief summary
```

### Session Log Entries

```markdown
## Session N - <YYYY-MM-DD>

### Completed

- Created `FeatureComponent` with translations
- Fixed backend validation bug in `expenses.py`
- Added test coverage for edge cases

### Blockers / Next Steps

- Waiting for user input on design
- TODO: Update user guide
```

---

## Formatting Standards

### Prettier for Markdown

All `.md` files use Prettier (80-char line width).

```bash
# Format single file
npx prettier --write path/to/file.md

# Format all markdown
npm run format:md
```

### Writing Style

- Use **active voice**
- Keep sentences **concise**
- Use **code blocks** for commands and paths
- Use **tables** for structured data
- Include **examples**

---

## Key Files to Update

### GEMINI.md

Update when:
- New development principles established
- Tech stack changes
- New troubleshooting solutions discovered
- Workflow commands change

**Sections:**
- Goal, Tech Stack, Localization
- Development Principles (8 principles)
- Project Structure, Key Commands
- Testing, Documentation Strategy
- Troubleshooting

### README.md

Update when:
- Major features added
- Setup instructions change
- New prerequisites required

### User Guides (docs/guides/)

Existing guides:
- `google-sheets-integration.md` - Google Sheets sync
- `backend-setup.md` - Backend installation
- `frontend-setup.md` - Frontend installation

---

## Verification Checklist

- [ ] Content in correct directory
- [ ] Added to `index.rst` (if Sphinx)
- [ ] Prettier-formatted: `npx prettier --check file.md`
- [ ] Links tested and working
- [ ] Code examples are accurate
- [ ] `PROGRESS.md` reflects current state
