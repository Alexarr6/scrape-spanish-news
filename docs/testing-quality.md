# Testing and quality

## Canonical local gate

```bash
make check
```

That runs:

- `make pre-commit`
- `make test`

## Other useful checks

### Backend lint only

```bash
make lint
```

### Frontend build verification

```bash
make frontend-check
```

### Docs verification

```bash
make docs-build
```

## What to verify after doc-oriented changes

- README commands still exist in `Makefile`
- docs nav paths still exist and links resolve
- frontend instructions still match `frontend/package.json`
- API startup notes still match `make api` and `src/api/app.py`
- semantic workflow notes still match the actual scripts and shared date-window logic

## Test posture

This repo already has meaningful tests, especially around API behavior and semantic/persistence contracts. The docs should lean on those tests as evidence, not invent confidence they have not earned.
