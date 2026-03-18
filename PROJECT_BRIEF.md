# PROJECT_BRIEF.md

## 1) Project name
Spain News Bias Scraper — semantic explorer app foundation (Phase 0 + Phase 1)

## 2) Objective (1-2 sentences)
Plan and implement the first serious application phase for the semantic explorer, moving from the current static HTML export to a proper 2D app foundation using deck.gl. This cycle should establish the frontend architecture, data flow, and an initial usable app shell without expanding into 3D yet.

## 3) Technical context
- Repo/path: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper`
- The project already has:
  - Postgres + pgvector semantic persistence
  - embeddings and projections persisted
  - semantic neighbors
  - a static 2D semantic explorer HTML
  - bounded semantic analysis and explorer usability improvements
- The current static HTML is useful but clearly reaching ergonomic limits
- The chosen direction is a more serious frontend based on **deck.gl**
- Multiple pages/views are allowed if justified, but avoid unnecessary product sprawl
- This project will now iterate phase-by-phase with the loop:
  - planner -> human gate -> implementer
- Each implementation phase must keep tests green and use atomic git commits

## 4) Inputs / Outputs
- Inputs: existing semantic backend/pipeline, current static explorer behavior, current semantic artifacts and query capabilities, and the decision to use deck.gl
- Outputs: a bounded architecture plan plus the first implementation pass for an app shell and core 2D explorer foundation

## 5) In scope
- [x] Define the application architecture for the semantic explorer app
- [x] Choose the practical frontend/backend integration shape for the first app phase
- [x] Build the first usable app shell around a 2D deck.gl-based explorer
- [x] Define or implement a clean data-loading path for the app using the current semantic backend as source of truth
- [x] Include a basic but serious inspector/filter interaction model for the initial app shell
- [x] Allow multiple pages/views only if they clearly help and remain bounded
- [x] Require atomic git commits during implementation

## 6) Out of scope (do-not)
- [x] Do not implement 3D in this cycle
- [x] Do not rewrite the scraper or semantic backend architecture
- [x] Do not broaden into auth, deployment platform work, or multi-user systems
- [x] Do not turn this into a giant frontend framework migration beyond what is needed for the app shell
- [x] Do not add speculative roadmap work from later phases into this implementation pass

## 7) Acceptance criteria
- [x] The planner defines a clear app architecture and first-phase implementation plan
- [x] The implementation delivers a usable 2D app shell that is a meaningful step up from the static HTML
- [x] The app is grounded in the existing semantic source of truth and does not invent a parallel semantic system
- [x] Filters/selection/inspection are present at a basic but serious level
- [x] Existing tests remain green and new behavior is verified
- [x] Implementation uses atomic commits per logical completed task

## 8) Required tests / verification planning
- [x] Existing repo gate remains green (`make check`)
- [x] New frontend/app behavior has practical smoke validation
- [x] Data loading path is verified against current semantic backend outputs/state
- [x] Commit history reflects atomic logical progress

## 9) Expected delivery
- Format: updated `PLAN.md`, then bounded implementation of the first app foundation phase
- Contents: architecture choice, file/module plan, verification plan, deferred items, and a clean implementation handoff

## 10) Risks / constraints
- Avoid replacing a simple working tool with an overengineered frontend toy
- Keep current semantic data model as the source of truth
- Preserve boring operational behavior while improving product ergonomics
- Keep this cycle focused on architecture + 2D app foundation only
