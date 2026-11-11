# AI Usage Log

This folder holds all prompts submitted to AI tools (Claude as technical lead, Google Antigravity as implementation agent) throughout the project.

## Numbering Convention

Prompts are organized using the naming pattern:
`NNN_<tool>_<short-topic>.md`

- `NNN`: Zero-padded three-digit sequential number (e.g., `001`, `002`).
- `<tool>`: Name of the AI tool used (e.g., `claude`, `antigravity`).
- `<short-topic>`: Brief slug describing the topic or task.

## Where AI was used / what I personally reviewed

| Date/Time (IST) | Prompt File | AI Tool | Task / Scope | What I Personally Reviewed |
| :--- | :--- | :--- | :--- | :--- |
| 2026-11-10 23:30 | [`001_claude_scaffolding_and_decisions.md`](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/ai-usage/prompts/001_claude_scaffolding_and_decisions.md) | Claude | Initial repo scaffolding, Decisions D1-D9, timeline and stack | Scoped 18m timeline, verified SQLite stack, checked D1-D9 feasibility |
| 2026-11-11 10:15 | [`002_claude_phase2_architecture_package.md`](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/ai-usage/prompts/002_claude_phase2_architecture_package.md) | Claude | Phase 2 Architecture Package, pipeline flow, ADR-001-012, ERD, and schema | Confirmed ADR-004 temporal design, ADR-007 randomization, and roadmap |
| 2026-11-11 10:30 | [`003_antigravity_phase2_approval_and_docs.md`](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/ai-usage/prompts/003_antigravity_phase2_approval_and_docs.md) | Antigravity | Architecture approval, generating `docs/02_architecture.md`, `docs/01_requirements_spec.md`, and prompt logs | Verified documentation integrity, ADR alignment, and test matrices |
