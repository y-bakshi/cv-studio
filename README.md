# CV Studio

[![CI](https://github.com/y-bakshi/cv-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/y-bakshi/cv-studio/actions/workflows/ci.yml)

CV Studio is a multi-user, LaTeX-backed résumé workspace with visual editing,
source editing, server-side PDF compilation, revision history, annotations, and
job-description storage.

The interface combines a document library with an Overleaf-style workspace:

- **Visual** — edit a structured résumé on a page-like canvas.
- **TeX** — inspect or edit the generated LaTeX source.
- **PDF** — view and download the authoritative `pdflatex` output.
- **Review** — attach annotations and job descriptions to a CV.

## Current capabilities

- Email/password registration and secure, HTTP-only database sessions.
- User-scoped CV storage and access control.
- CV library, folders, titles, and starred documents.
- Tiptap/ProseMirror visual editor with formatting and highlighting.
- Stable IDs on supported visual document blocks.
- Generated LaTeX plus an advanced source-editing mode.
- Asynchronous `pdflatex` compilation with timeouts and shell escape disabled.
- Protected PDF preview and direct server-generated PDF download.
- Optimistic version checks to prevent silent concurrent overwrites.
- Automatic revision history and revision restore.
- Text-selection annotations and right-click review actions.
- Pasted job descriptions and uploads from TXT, Markdown, or text-based PDF.
- PostgreSQL support with SQLite as the zero-configuration development default.
- shadcn/ui components with Tailwind CSS v4.

AI is deliberately separated from the document write path. A future provider
adapter can use Ollama or hosted models to generate reviewable change proposals;
the user will approve a structured diff before a proposal changes a CV.

## Technology

| Layer | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite |
| Component system | shadcn/ui, Tailwind CSS, Radix UI |
| Visual editor | Tiptap/ProseMirror |
| API | FastAPI, Python |
| Persistence | SQLAlchemy; PostgreSQL or SQLite |
| PDF generation | `pdflatex` |
| PDF preview | PDF.js via React-PDF, backed by protected API artifacts |
| PDF ingestion | pypdf |
| Authentication | Random server-side sessions; `scrypt` password hashing |

## Repository layout

```text
cv-studio/
├── apps/
│   ├── api/                    # FastAPI routes, domain services, and tests
│   └── web/                    # React features, shared components, and API client
├── artifacts/                  # generated PDFs; ignored by Git
├── legacy-prototype/           # original dependency-free UX prototype
├── compose.yml                 # PostgreSQL and Redis development services
├── Makefile
└── README.md
```

`PLAN.md` is intentionally local-only and ignored by Git.

## Architecture

The API uses a small layered structure:

- `routers/` owns HTTP concerns: authentication, validation dependencies,
  status codes, and response handling.
- `services/` owns reusable operations such as revision snapshots, upload text
  extraction, and queued LaTeX compilation.
- `schemas.py` defines request contracts; `serializers.py` defines safe response
  shapes; `models.py` is persistence only.
- `main.py` creates the application and registers routers. It should not contain
  feature logic.

The web client is organized by responsibility:

- `features/workspace/` owns the editor workspace, its controller hook, and
  feature-level views.
- `features/assistant/` contains the provider-independent proposal contract for
  the future AI workflow.
- `components/` contains reusable product components, while `components/ui/`
  contains shadcn primitives.
- `lib/api.ts` is transport only and `lib/types.ts` contains shared client-side
  domain types.

Comments document security boundaries, lifecycle behavior, or non-obvious
decisions. Routine code is kept readable instead of being narrated line by line.

## Planned work

Actionable `TODO(...)` markers in the code identify the intended integration
boundaries:

- `TODO(database-migrations)` — replace startup `create_all` with Alembic.
- `TODO(durable-compilation)` — move compilation to a Redis-backed, sandboxed
  worker.
- `TODO(realtime-compilation)` — replace client polling with server events.
- `TODO(job-link-ingestion)` — accept job-posting URLs with SSRF-safe fetching.
- `TODO(ai-provider)` — add Ollama and hosted adapters that return structured,
  user-approved changes.

These are deliberately not fake implementations. In particular, no model output
will write directly to a CV; the assistant contract produces reviewable proposals.

## Requirements

- Python 3.11+
- Node.js 20+
- npm
- `pdflatex` with the standard packages used by the generated template
- Docker, only when using the provided PostgreSQL/Redis services

## Quick start

Install dependencies:

```bash
make install
```

Start the API in one terminal:

```bash
make dev-api
```

Start the web application in another:

```bash
make dev-web
```

Open <http://localhost:5173>, create an account, and create a CV.

The default development database is `cv-studio.db`, which is ignored by Git.

## PostgreSQL development

Start infrastructure:

```bash
docker compose up -d postgres redis
```

Then start the API with the PostgreSQL connection:

```bash
DATABASE_URL=postgresql+psycopg://cvstudio:cvstudio@localhost:5432/cvstudio make dev-api
```

Redis is provisioned for the next step of moving compilation from the local
executor to a separately deployable worker. The current API already queues jobs
off the request path using a bounded executor.

## Validation

Run backend integration tests and build the production frontend:

```bash
.venv/bin/pytest apps/api/tests -q
cd apps/web && npm run build
```

The API tests cover:

- registration and authenticated sessions;
- user data isolation;
- CV creation and editing;
- optimistic concurrency conflicts;
- revision creation;
- annotations; and
- job-description persistence.

## Compilation model

Visual documents are serialized into an approved LaTeX template. Compilation:

1. snapshots the current CV revision;
2. writes TeX into an isolated temporary directory;
3. invokes `pdflatex` twice with shell escape disabled;
4. enforces a timeout;
5. persists the compiler log and PDF artifact; and
6. exposes the artifact through an authenticated download endpoint.

For production, the compiler should additionally run inside a locked-down
container with CPU, memory, process, filesystem, and network limits.

## Security notes

- API queries scope every CV-related record to the authenticated user.
- Passwords use salted `scrypt`; raw passwords are never stored.
- Session cookies are HTTP-only and same-site.
- Set `SECURE_COOKIES=true` behind HTTPS.
- LaTeX shell escape is disabled.
- Uploads are type- and size-limited.
- Generated files, databases, local plans, secrets, and dependencies are ignored.
- AI providers will not receive résumé data without explicit server configuration.

## Configuration

See [.env.example](.env.example). Supported variables:

- `DATABASE_URL`
- `FRONTEND_ORIGIN`
- `ARTIFACT_ROOT`
- `SESSION_DAYS`
- `SECURE_COOKIES`
- `COMPILE_TIMEOUT_SECONDS`

## Legacy prototype

The first UX prototype remains under `legacy-prototype/` for reference. It is
not used by the React/FastAPI application.

## License

No open-source license has been selected yet. All rights are reserved until a
license file is added.
