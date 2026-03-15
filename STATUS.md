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

## Blockers
- the actual scraper code still lives under a historical run directory today; ops now bridge to it instead of pretending root is already promoted
- persistent runs and API still require a real `DATABASE_URL`

## Next steps
- run `make preflight`
- run `make test`
- run one manual scrape from repo root
- export `DATABASE_URL` and run `make scheduler-once`
- install cron outside git if the human wants the proposed schedule
