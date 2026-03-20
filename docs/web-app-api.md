# Web app and API

## App factory

The FastAPI app lives in `src/api/app.py` and is created with:

```bash
uv run python -m uvicorn src.api.app:create_app --factory
```

The `make api` target wraps that with the repo-root environment and required `DATABASE_URL` check.

On startup the app currently:

- resolves the Postgres URL
- creates the SQLAlchemy engine
- initializes base persistence schema
- wires the shared session dependency override
- mounts the article, cluster, and semantic routers
- mounts `/explorer` and `/assets` only when `frontend/dist` exists

## API surfaces

### `/api/v1/articles`
Persistence-backed article endpoints.

### `/api/v1/clusters`
Story-cluster list, filter, and detail endpoints backed by analysis read-side queries.

### `/api/v1/semantic/explorer`
Semantic explorer list, filter, and article-detail endpoints backed by semantic storage/read-side queries.

## Frontend workspace

The UI lives in `frontend/` and uses Vite + React + TypeScript.

Important commands from `frontend/package.json`:

```bash
cd frontend && npm run dev
cd frontend && npm run build
cd frontend && npm run preview
```

## Development split

For normal UI work, keep the backend API and Vite server in separate terminals.

Terminal 1:

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make api
```

Terminal 2:

```bash
cd frontend && npm run dev
```

## Story browser vs semantic explorer

The frontend currently switches views with query-string state rather than a heavyweight routing setup.

- default mode: story cluster browser
- `?view=semantic`: semantic explorer mode

URL-state hooks in `frontend/src/hooks/` serialize filters and selection back into the query string so refreshes and deep links preserve operator context.

## Built frontend serving

If `frontend/dist/index.html` exists, FastAPI serves the built explorer shell at `/explorer`. That is a convenience for local packaged testing, not a substitute for Vite during frontend development.
