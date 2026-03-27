IMPLEMENTATION_DONE

iter/030 completed the documentation cleanup, root de-cluttering, and English-normalization pass.

Completed work:
- moved tracked root audits/reviews/specs into `docs/historical/` subfolders
- moved retained process artifacts out of repo root into `docs/historical/process/`
- removed the stray root `info.txt` note
- clarified `README.md` + `docs/` as the canonical documentation surface
- updated MkDocs nav so moved historical docs remain discoverable
- relocated agent scaffolding for iter/030 under `.agent/iter-030/`

Verification:
- attempted `make docs-build` (blocked: `uv missing` in this environment)

Next state:
- implementation finished; repo root should now contain only active entry docs and normal project files
