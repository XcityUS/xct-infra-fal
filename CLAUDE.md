# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AGENTS.md hierarchy (read first)

This repo follows a layered `AGENTS.md` convention. Always consult the `AGENTS.md` closest to the files you are changing; if rules conflict, the nearer file wins.

- `/AGENTS.md` — global defaults (team preferences, generated-code policy, commit format)
- `projects/fal/AGENTS.md` — SDK/CLI/runtime rules, including Windows compatibility requirements
- `projects/fal_client/AGENTS.md` — client-specific test guidance
- `projects/isolate_proto/AGENTS.md` — strict generated-code policy for protobuf bindings

The root `AGENTS.md` is the source of truth for the pre-merge checklist; do not duplicate that information here — read it.

## Monorepo layout

Three installable Python packages under `projects/`:

| Package | Path | Role |
| --- | --- | --- |
| `fal` | `projects/fal` | SDK + CLI + serverless runtime (`fal run`, `fal deploy`) |
| `fal_client` | `projects/fal_client` | Lightweight sync/async HTTP client for calling fal endpoints |
| `isolate_proto` | `projects/isolate_proto` | gRPC/protobuf definitions consumed by `fal` |

Dependency direction: `fal` → `isolate_proto` (via gRPC) and `fal` ↔ `fal_client` (test-only). Editable installs are independent — install only the package you are changing.

## Architecture notes that span files

- **`projects/fal/src/fal/app.py` + `api/`**: `fal.App` and `@fal.endpoint` are the user-facing entrypoints. `app.py` wires user classes into FastAPI; `api/` hosts the gRPC client to the fal control plane (`api/client.py`, `api/runners.py`, `api/deploy.py`).
- **Cloudpickle serialization boundary**: a specific set of modules under `projects/fal/src/fal/` get cloudpickled and shipped to remote workers (`_serialization.py`, `app.py`, `api/api.py`, `auth/__init__.py`, `config.py`, `container.py`, `exceptions/_base.py`, `exceptions/_cuda.py`, `ref.py`, `sdk.py`, `toolkit/file/file.py`, `toolkit/file/providers/fal.py`). Lazy/in-function imports in these files are banned by Ruff rule `PLC0415` — keep imports module-level or follow the existing pattern in the file.
- **`projects/fal/openapi-fal-rest/`**: generated OpenAPI client. Never hand-edit; regenerate with `openapi-python-client` using `projects/fal/openapi_rest.config.yaml`.
- **`projects/isolate_proto/src/isolate_proto/*_pb2{,_grpc}.py{,i}`**: generated protobuf bindings. Never hand-edit; regenerate with `python tools/regen_grpc.py --isolate-version <isolate-tag-without-v>`.
- **CLI lives under `projects/fal/src/fal/cli/`**, dispatched from `cli/main.py`. Toolkit (`fal/toolkit/`) is the user-facing helper surface (`file/`, `image/`, `audio/`, `video/`, `kv.py`).

## Common commands

Setup (from repo root, only install what you are touching):

```bash
pip install -e 'projects/fal[dev]'
pip install -e 'projects/fal_client[dev]'
pip install -e 'projects/isolate_proto[dev]'
```

Validation loop — **`pre-commit` is required**, it gates CI:

```bash
pre-commit run --all-files
```

Tests (run the smallest relevant scope first):

```bash
# fal — unit (always runnable)
pytest -n auto -v projects/fal/tests/unit
# fal — a single test file
pytest -v projects/fal/tests/unit/test_app.py
# fal — integration (requires credentials)
FAL_KEY=... FAL_HOST=api.fal.dev FAL_RUN_HOST=run.fal.dev \
  pytest -n auto -v projects/fal/tests/integration
# fal — e2e (requires credentials)
FAL_KEY=... FAL_GRPC_HOST=api.fal.dev FAL_RUN_HOST=run.fal.dev \
  pytest -n auto -v projects/fal/tests/e2e

# fal_client
pytest projects/fal_client/tests
pytest projects/fal_client/tests/unit  # offline-only subset

# isolate_proto
pytest projects/isolate_proto/tests
```

If credentials are unavailable, run only unit/local tests and say so explicitly — do not attempt integration/e2e.

Docs (combines SDK + client):

```bash
make docs   # output under docs/_build/html/{sdk,client}
```

Regenerate gRPC bindings:

```bash
cd projects/isolate_proto && pip install -e '.[dev]'
python ../../tools/regen_grpc.py --isolate-version <isolate-tag>
pre-commit run --all-files
```

## Hard rules

- **Pre-commit before finishing** — non-negotiable. Ruff format/lint runs on `projects/fal/src/`, `projects/fal/tests/`, and `projects/fal_client/`. MyPy runs on `projects/fal/src/`.
- **Never hand-edit generated code**: `*_pb2.py`, `*_pb2.pyi`, `*_pb2_grpc.py`, anything under `projects/fal/openapi-fal-rest/`. Regenerate instead.
- **Conventional Commits**: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:` — scope form encouraged (`fix(cli): …`).
- **Windows compatibility for `fal` CLI/runtime**: avoid POSIX-only modules (`fcntl`, `termios`, `tty`, executable bits, symlinks) without a fallback; use `pathlib`/`os.replace`; route console glyphs through `fal.console.icons` / `fal.console.rules.print_rule` for non-UTF terminals. Windows CI runs the full unit suite.
- **No secrets in tests** — if a test needs `FAL_KEY` and you don't have one, skip it; do not commit credentials or write fixtures that bake in real keys.

## Test placement (fal package)

- CLI changes → `projects/fal/tests/unit/cli/`
- Toolkit changes → `projects/fal/tests/unit/toolkit/`
- Cross-service behavior → `projects/fal/tests/integration/` or `tests/e2e/`
