# Stage 1 Acceptance Criteria

This file lists the conditions that must be met before Stage 1 is considered complete and Stage 2 can begin.

## Mandatory (must pass)
- [x] `backend/contracts.md` exists and defines the core HTTP endpoints and WebSocket message formats used by GenCode Studio.
- [x] Integration manager and test agent adapter hooks are present in `backend/src/routes/agents.ts` and support `mock` mode for local runs.
- [x] `MONGO_URL` fallback implemented and backend default port set to 8001 (or honors `PORT` env override).
- [x] An example `supervisor.backend.conf` is present in repo root.
- [x] A basic design tokens file exists at `design/tokens.json` that front-end developers can consume.

## Recommended (should pass)
- [ ] Decision checklist documented with required credentials and owners in `discovery/decision-checklist.md`.
- [ ] Feature mapping exists linking reference product features to GenCode implementation (`discovery/feature-mapping.md`).

## Exit criteria
- All mandatory items satisfied.
- At least one developer has run the mock happy-path end-to-end (workflow initiation -> mocked LLM responses -> mocked test reports) and confirmed no runtime errors in logs.

Once the above are met, Stage 2 (Implementation & Parity) can proceed.

