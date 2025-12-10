# Decision & Resource Checklist

These items must be decided/collected to proceed into Stage 2 implementation with minimal delays.

## Credentials & Endpoints
- [ ] `UNIVERSAL_LLM_KEY` (or GENERIC API key) for integration manager (if using real gateway).
- [ ] `INTEGRATION_MANAGER_URL` for LLM forwarding (or confirm using `mock` for staging).
- [ ] `TEST_AGENT_URL` for remote testing (or confirm `mock`).
- [ ] `MONGO_URL` for production DB credentials (staging DB connection string if testing beyond mock).

## Design & Branding
- [ ] Landing page copy & hero assets (images or illustrations) and permission to use any third-party assets.
- [ ] Trust logos and legal blurbs to display (if replicating the reference site's trust strip).
- [ ] Confirm font licensing for `Space Grotesk` and `Inter` (or provide preferred fonts).

## Operational decisions
- [ ] Confirm that backend must bind to `0.0.0.0:8001` in production.
- [ ] Confirm process manager choice (supervisor example included). Provide process owner and log locations.
- [ ] Decide SSO providers to enable (Google / GitHub / Apple) and provide OAuth credentials and redirect URIs.

## Testing & QA
- [ ] Decide whether the external test agent will be used in staging/production or tests will be local.
- [ ] Provide acceptance criteria owners and who will review `test_result.md` output.

## Legal & Compliance
- [ ] Approve reuse of any reference-site copy or images (or instruct to generate original copy).
- [ ] Confirm privacy policy or data handling constraints for user-submitted prompts/assets.


## Other Resources
- [ ] Design resource owner and Figma link (if available)
- [ ] Ops contact for deployment and supervisor installation


---
Update this checklist as items are obtained. Items marked required must be present before Stage 2 starts for fastest path.