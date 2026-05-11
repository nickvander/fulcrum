---
name: Work Handoff
description:
  Read, update, archive, and prepare Fulcrum's work/ handoff files so a new
  agent can safely continue from the current product context.
---

# Work Handoff Skill

Use this skill when the user asks what is next, wants to start a new
conversation, asks whether `work/` is ready for the next agent, or asks to clean
up completed work.

## Start Here

Always read these files first:

1. `work/current/PROGRESS.md`
2. The active current plan linked from `PROGRESS.md`
3. `work/current/MISSING_ITEMS.md`
4. The latest matching archive file in `work/archive/`

Then check the repo state:

```bash
git status --short
git log --oneline -5
```

## Work Directory Rules

- `work/current/` contains only active or next-session work.
- `work/archive/` contains completed plans/logs.
- `work/current/PROGRESS.md` is the entry point for the next agent.
- `work/current/MISSING_ITEMS.md` tracks remaining gaps and guardrails.
- Move completed work to `work/archive/` once it is verified and committed.
- Keep marketplace allocation separate from PO receiving:
  - PO receiving updates Fulcrum internal inventory only.
  - Do not auto-sync received stock to Amazon or MercadoLibre.
  - Marketplace quantities require a later allocation/planning workflow.

## Preparing A Next Session

When ending or preparing a session:

1. Archive completed current work.
2. Create one concise next-slice file in `work/current/`.
3. Update `work/current/PROGRESS.md` with:
   - current status
   - current work file
   - next session starting point
   - recent archive links
4. Update `work/current/MISSING_ITEMS.md` so completed items are checked off.
5. Run verification appropriate to the changes.
6. Commit and push.
7. Confirm `git status --short` is clean.

## Suggested Next-Slice Template

```markdown
# <ID>: <Title>

## Goal

One paragraph describing why this is next.

## Completed Baseline

- What is already working.
- What was verified.

## Best Next Features

1. Highest-impact next feature.
2. Second best feature.
3. Guardrail or cleanup item.

## Verification To Keep

- Backend tests to rerun.
- Frontend tests/build to rerun.
- Browser smoke path to preserve.
```

## Cleanup Rules

- Remove root-level generated logs and stale test output files unless they are
  intentional documentation.
- Do not remove source, fixtures, migrations, or user-created artifacts unless
  the user explicitly asks.
- Prefer keeping useful sample artifacts under an intentional path such as
  `backend/samples/`.

## Completion Checklist

- [ ] `work/current/PROGRESS.md` points to the right active file.
- [ ] Completed work is in `work/archive/`.
- [ ] `MISSING_ITEMS.md` reflects reality.
- [ ] Tests/builds relevant to the change pass.
- [ ] Repo root has no accidental log/test-output clutter.
- [ ] Commit is pushed.
- [ ] `git status --short` is clean.
