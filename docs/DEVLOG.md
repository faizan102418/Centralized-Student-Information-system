# Development Log

Running record of daily work on the production/research phase. Kept
honest — including bugs and dead ends, not just successes — since this
doubles as raw material for the Phase 4 research write-up.

---

## Day 1 — 2026-08-21

**Plan:** Repo/DevOps setup + FastAPI backend foundation (merged Days 1-7
of the original plan into one session).

**Shipped:**
- `.pre-commit-config.yaml` — ruff lint/format + basic file hygiene hooks
- FastAPI backend (`src/chatbot/api/`) reusing the existing `auth`,
  `database`, `rag_pipeline` modules — no logic duplicated
- JWT-based auth (`/auth/login`) replacing Streamlit's session-only login,
  so the API works from any client
- `/chat` endpoint enforces the same RBAC as the Streamlit app, and logs
  every query to `query_logs` (session id, role, latency, access_denied)
- `Dockerfile` + `docker-compose.yml` (MySQL + API) — built, not yet
  tested end-to-end
- Fixed a real GitHub gotcha: commits were landing on a **fork**, which
  doesn't count toward the contribution graph. Migrated to a standalone
  repo (`Centralized-Student-Information-system`) and preserved full
  history/authorship.

**Bugs hit and fixed (all real, all logged for the record):**
1. `ModuleNotFoundError: chatbot.auth` — a delivered `__init__.py` was
   misnamed; sorted via directory listing.
2. `/health` degraded + `/auth/login` 500 — MySQL wasn't running in this
   session; not a code bug.
3. Swagger's "Authorize" button failed with `OAuth2PasswordBearer` since
   our login endpoint takes JSON, not OAuth2 form data. Switched to
   `HTTPBearer` for a simple paste-your-token flow.
4. First commit attempt was silently blocked by pre-commit's `ruff` hook
   auto-fixing a file — had to re-stage and re-commit.

**Verified working:** login → JWT → RBAC-protected `/chat` → response
logged to `query_logs`, including a confirmed access-denied case (student
role blocked from another student's record, logged with `access_denied=1`,
latency 0ms since it short-circuits before calling Groq).

**Not done yet:** Docker Compose stack untested end-to-end. Streamlit
still talks to the `chatbot` package directly rather than the new API.

---

## Day 2 — (planned)

- Bring up the full Docker Compose stack (MySQL + API) and verify `/health`
  and `/chat` work identically inside containers as they did locally.
- Depending on time: begin the DB schema upgrade (UUID-based student IDs
  instead of name-based linking) from the original Day 8-10 plan.
