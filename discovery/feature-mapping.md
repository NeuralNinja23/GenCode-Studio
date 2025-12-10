# Feature Mapping — Reference Product -> GenCode Studio

This document maps the reference product's features and behaviors to the current GenCode Studio implementation (file references and notes). Use this to prioritize parity work.

## Core agentic flows
- Reference: Multi-agent pipeline (planner, coder FE, coder BE, modifier, contract agent, backend tester, frontend tester, deployment agent)
- GenCode implementation: `backend/src/routes/agents.ts` contains planner (`runPlanAndArchitect`), coder batches (`runCoderBatch`), modifier (`runModifier`), backend/frontend testers (`runBackendTester`, `runFrontendTester`), deployment agent (`runDeploymentAgent`).
- Parity note: Agent names, temperatures and model routing are already expressed in the code; adapters exist to route LLM calls to an integration manager.

## Preview & per-workspace dev servers
- Reference: Start a per-workspace dev server, capture preview URL, and emit `BUNDLE_RESPONSE` events.
- GenCode implementation: `backend/src/server.ts` startViteDevServer() spawns `yarn dev` for a workspace, listens for localhost URL in stdout/stderr and sends `BUNDLE_RESPONSE` via WebSocket.
- Parity note: Behavior is implemented and WS messages match expected formats.

## Testing pipeline
- Reference: Named testing agents, canonical `test_result.md` updated by test agent.
- GenCode implementation: `runBackendTester` / `runFrontendTester` produce TestReport object; `test_result.md` read/write utilities exist in `agents.ts` (readTestResults). Adapter hooks exist to forward to external test agent (mock-capable).
- Parity note: Needs final wiring to external test agent endpoint for full parity; local LLM-based testing is available.

## Integration manager / universal LLM key
- Reference: Centralized integration manager and universal key for all LLM calls.
- GenCode implementation: Integration adapter hook added in `agents.ts` (INTEGRATION_MANAGER_ENABLED / INTEGRATION_MANAGER_URL) with mock support; direct provider calls remain as fallback.
- Parity note: Adapter exists; requires production endpoint and key to be fully equivalent.

## API & Runtime conventions
- Reference: All API routes prefixed `/api`, backend binds to 0.0.0.0:8001, DB via `MONGO_URL`.
- GenCode implementation: Routes mounted under `/api/*` in `backend/src/server.ts`, default port set to 8001, DB accepts `MONGO_URL` fallback in `backend/src/lib/db.ts`.
- Parity note: Conventions aligned.

## Frontend UI & marketing
- Reference: Polished landing, signup flows, trust strip, hero, feature showcase.
- GenCode implementation: Functional workspace UI present (`frontend/src/pages/*`), but landing and marketing pages need to be implemented or enhanced to match reference product visuals and copy.
- Parity note: Work required (design tokens, hero, signup, SSO) for full parity.

## Developer playbook
- Reference: Strict developer rules for mocks, components, file layout, contracts.md.
- GenCode implementation: Many checks and rules enforced in `agents.ts` prompts and code generator contexts; `contracts.md` will be added (this stage).
- Parity note: Close — coders use inline rules; formal developer README and sanitized playbook will be produced.

## Summary & priorities (for Stage 2)
1. Finalize integration manager endpoint and universal key (adapter wiring).
2. Wire external test agent endpoints or finalize mock agent for staging.
3. Implement landing and signup UI parity (copy + assets).
4. Produce final developer README and public-safe playbook.

