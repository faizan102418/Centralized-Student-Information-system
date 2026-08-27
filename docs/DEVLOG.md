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

## Day 2 — 2026-08-22

**Plan:** Get the full Docker Compose stack (MySQL + API) running and
verified end-to-end.

**Shipped:**
- Fixed `torch` pulling in the full CUDA/NVIDIA toolkit (~2GB of unused
  GPU libraries) inside the Docker build by pinning it to PyTorch's
  CPU-only wheel index via `[tool.uv.sources]` — required making `torch`
  a direct dependency, since `uv` only applies source overrides to
  packages the project explicitly declares, not transitive ones.
- Fixed a `Dockerfile` build failure: `hatchling` needs `README.md`
  present to validate package metadata, but our layer-caching strategy
  only copied `pyproject.toml`/`uv.lock` before `uv sync` — added
  `README.md` to that early `COPY`.
- Fixed a duplicate-seed-data crash: `add_users.sql` (a fix built for
  patching an *existing* local MySQL) was redundant against a *fresh*
  container where `seed.sql` already creates the same accounts — removed
  it from `docker-compose.yml`'s init scripts.
- Verified the full stack end-to-end inside containers: MySQL init
  scripts run cleanly, API connects via the `mysql` service hostname
  (not `localhost`), embedding model downloads and loads, login → JWT →
  RBAC-protected `/chat` → logged to `query_logs`, confirmed via
  `docker exec` directly against the containerized database.

**Bugs hit and fixed (debugging methodology practiced, not just patched):**
1. `uv.lock` kept resolving `torch` from PyPI despite the override —
   walked through ruling out syntax, then cache staleness (full
   `uv cache clean`, 5.5GB), before finding the real cause: direct vs.
   transitive dependency scoping in `uv`.
2. Docker build failed on a missing `README.md` — traced to which files
   get copied into which build stage, and when.
3. MySQL init crashed on `Duplicate entry 'admin'` — traced to two
   different seed files, each correct for a different scenario (patching
   existing data vs. fresh init), that conflicted when both were mounted.

**Key lesson practiced today:** verify each fix with the cheapest
possible check before re-running the expensive one (`Select-String` on
`uv.lock` in milliseconds, instead of a multi-minute Docker rebuild every
time).

**Not done yet:** No persistent cache for the embedding model inside
Docker — it re-downloads on every fresh container build. Worth a volume,
same pattern as `mysql_data`, before this goes to real deployment.

---

## Day 3 — 2026-08-23 (light session, Sunday)

**Plan:** One small, contained task — HuggingFace embedding model caching
in Docker. Kept deliberately light; UUID student ID migration deferred
whole to Day 4.

**Shipped:**
- Added a named `hf_cache` volume to `docker-compose.yml`, mounted at
  `/app/.cache/huggingface`, with `HF_HOME` pointed at it. The embedding
  model now downloads once and persists across container restarts,
  instead of re-downloading ~400MB every fresh `docker compose up`.

**Not done (intentionally, deferred to Day 4):**
- UUID-based student ID migration (schema change + query updates across
  `database.py`, `auth.py`, seed data) — this is a real, multi-file
  change that deserves full focus, not a Sunday half-session.

---

## Day 4 — 2026-08-24

**Plan:** Start the UUID-based student ID migration (expand-contract
pattern). Scoped down to 3-4 commits since today had less available time
- full pipeline integration and old-column cleanup deferred to Day 5.

**Shipped:**
- `data/migrations/002_add_student_uuid.sql` - additive migration:
  backfills `student_id` (UUID) into `student_general_data`,
  `student_scholarship`, `student_fee_submission`, and `users`, matched
  via name (the last time this codebase relies on name-matching).
  Existing name-based columns untouched - pure "expand" step.
- `data/seed.sql` updated so fresh installs get `student_id` from the
  start, no migration needed for new databases.
- `database.py`'s `fetch_student_data_from_db()` now merges records by
  `student_id` instead of lowercased name - the actual behavior change,
  eliminating the name-collision risk flagged in the thesis (11.1, 12.3).

**Bugs hit and fixed:**
1. XAMPP's `mysql.exe` turned out to be a 0-byte file (almost certainly
   antivirus quarantine neutering it) - pivoted to verifying entirely
   against Docker's MySQL instead of chasing that down mid-session.
2. `ADD COLUMN IF NOT EXISTS ... AFTER ...` isn't valid syntax on this
   MySQL version - dropped the `IF NOT EXISTS` (not essential, the
   migration only needs to run once anyway).
3. Docker port 3306 conflict blocked `docker compose up` - a leftover
   process (likely XAMPP's `mysqld` server, separate from the broken
   CLI client) was still holding the port.
4. Forgot that `docker compose restart` reuses the existing image and
   won't pick up code changes - needed `--build` to actually rebuild.

**Verified:** Migration backfill confirmed consistent across all four
tables (same UUID for Alice Smith everywhere she appears). `/chat`
queries against Alice and Bob still return correct answers after
switching `database.py` to ID-based joins.

**Deferred to Day 5:**
- `rag_pipeline.py` / prompt-level awareness of `student_id`
- `auth.py`: derive `student_name` via `student_id` JOIN instead of the
  (now potentially stale) stored column, so a student's linked record
  can't drift out of sync
- Repair XAMPP's `mysql.exe` (not urgent - Docker is the working path)
- Eventually: remove old name-based columns (the "contract" step) once
  fully confident, not before
