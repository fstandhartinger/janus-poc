# Janus PoC (spec-first)

This repo contains implementation-grade specs for the Janus Proof-of-Concept. It does **not**
include a working implementation yet.

## Create the private GitHub repo

1) Create a new private repo under the `fstandhartinger` org/user named `janus-poc`.
2) From this folder, add the remote and push:

```bash
git remote add origin git@github.com:fstandhartinger/janus-poc.git
git push -u origin main
```

## Local run (once implemented)

The specs assume a two-service setup:
- `gateway/` (FastAPI, Python 3.11)
- `ui/` (Next.js, Node 20+)

Expected dev flow after implementation:

```bash
# Gateway
cd gateway
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn janus_gateway.app:app --host 0.0.0.0 --port 8080 --reload
```

```bash
# UI
cd ui
npm install
npm run dev
```

The gateway will be configured to talk to the local Sandy sandbox service. See
`specs/08_sandy_integration.md` for required environment variables.

## Contents

- `specs/` contains the full spec suite, OpenAPI docs, and examples.

## Notes

This repository is nested inside the Chutes monorepo but is intentionally **ignored** by the
monorepo `.gitignore`. It is meant to be managed as its own repo.
