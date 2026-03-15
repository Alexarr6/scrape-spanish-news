- State: IMPLEMENTED
- Current phase: root operator surface + scheduler wrapper added
- Last update: 2026-03-15 16:45 UTC

## Progress log
- [x] reviewed project brief / contract / plan template
- [x] reviewed current repo structure and runnable historical app roots
- [x] added root `Makefile` as canonical operator surface
- [x] added runtime detection bridge so root ops can prefer future root code and fall back to runnable legacy `runs/*`
- [x] added `scripts/run_scheduled.sh` with lock, retry, logs, and state files under root `var/`
- [x] documented root-first operation and cron usage
- [x] added optional local Postgres Docker Compose path at repo root
- [x] added root Makefile targets for local DB lifecycle and connectivity checks
- [x] documented exact local persistence and scheduler verification steps

## Blockers
- the actual scraper code still lives under a historical run directory today; ops now bridge to it instead of pretending root is already promoted
- persistent runs and API still require a real `DATABASE_URL` (external or the optional local Compose DB)
- this host may not have Docker/Compose available; the local DB path is implemented anyway, but runtime verification depends on the host tooling

## Next steps
- run `make preflight`
- run `make test`
- optional local DB path: `cp .env.example .env && make db-up && make db-check`
- export `DATABASE_URL="$(make --no-print-directory db-url)"` and run `make run-source-persist SOURCE=elpais`
- run `make scheduler-once && make verify-db && make status`
- install cron outside git if the human wants the proposed schedule
