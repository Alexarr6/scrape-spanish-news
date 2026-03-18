# TASK_CONTRACT.md

## Objective
Plan and implement the first serious semantic explorer app phase for `spain-news-bias-scraper`: establish the app architecture and deliver a usable 2D deck.gl-based app shell on top of the current semantic backend.

## Technical Context
- Repo/path: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper`
- The repo already has a working semantic backend and a static 2D explorer/export
- The next step is not more static HTML patching; it is a bounded app foundation phase
- deck.gl is the chosen frontend direction
- Multiple pages/views are allowed if clearly justified and bounded
- This project will iterate phase-by-phase via planner -> human gate -> implementer
- Implementation must create atomic git commits for each logical completed task

## Scope
- [x] Define the app architecture for the first serious frontend phase
- [x] Decide the practical frontend/backend data flow for this phase
- [x] Implement a usable 2D app shell using deck.gl
- [x] Provide basic bounded inspection/filtering/selection behavior
- [x] Keep the current semantic backend as the source of truth
- [x] Use atomic commits during implementation

## Non-goals
- [x] No 3D implementation in this cycle
- [x] No scraper/backend redesign
- [x] No auth/deployment/platform sprawl
- [x] No speculative future-phase implementation beyond what this foundation requires

## Acceptance Criteria (checklist)
- [x] `PLAN.md` defines one clear bounded app-foundation phase
- [x] The resulting app shell is a clear usability step beyond the static HTML export
- [x] The current semantic system remains the canonical backend/source of truth
- [x] Existing tests remain green and new behavior is verified
- [x] Commit history shows atomic logical progress

## Verification
Planner/implementer should include practical checks such as:
```bash
# repo gate
# frontend/app smoke checks
# data-loading path validation
# git log / commit granularity sanity check
```

## Delivery Expectations
- Main artifacts: updated `PLAN.md`, bounded implementation, passing verification, and atomic commits

## Safety Constraints
- Keep the phase small, practical, and grounded
- Do not break the current semantic persistence/query path
- Do not add 3D or product sprawl yet
- Use atomic commits rather than a single large dump commit
