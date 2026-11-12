# AI Usage Disclosure

## Tools used
- **Claude (Anthropic):** technical lead and reviewer. It drafted the requirement specification, the
  architecture and ADRs, the schema design, and the implementation prompts, and it reviewed each agent run.
- **Google Antigravity (AI coding agent):** wrote nearly all of the code, tests and documents from the
  prompts. I sent the prompts and the agent's reports back and forth between the two tools.

## Where AI accelerated the work
Requirements analysis, the architecture, the data generator, the model and experiment pipeline, the
detectors and evaluation, the dashboard and the documents.

## Where I relied heavily on AI
Nearly all code was written by Antigravity. The design (temporal split, planned-offer randomization,
hidden potential outcomes, blind detectors) was proposed by Claude. I approved it after reading
docs/02_architecture.md: I carefully reviewed the dual-snapshot temporal design ($P_0 = 2025\text{-}07\text{-}01$ for model training, $P = 2026\text{-}01\text{-}01$ for scoring) and confirmed that features strictly forbid events on or after the cutoff date, preventing lookahead leakage. I validated why planned offer assignment must precede 50/50 randomized arm allocation to avoid post-treatment selection bias, and why potential outcomes must live in an isolated `ground_truth/` directory so blind detectors can be audited objectively. During review, I questioned committing the 108 MB full dataset to Git (ADR-009) and decided to commit the complete 1,000-subscriber starter dataset while verifying the full 20,000-subscriber dataset via deterministic cryptographic SHA-256 manifests. I also rejected running a separate background FastAPI daemon, replacing it with a direct read-only services layer (`src/churnexp/services/queries.py`) consumed by Streamlit.

## What I personally did and validated
- Chose the stack (Python only, Streamlit instead of React) and approved each phase and milestone.
- Ran the tests and key commands in my own terminal instead of trusting the agent's reports, and made all
  git commits myself.
- Declined a request from the agent to bypass its sandbox for git commands.
- Opened the dashboard and clicked through all five pages: On the *Support Agent* page, I noticed that inspecting a detector-flagged customer (e.g. from Anomaly B) clearly exposes the 7 eligibility rules with visual pass/fail badges, observed vs threshold values, and exact evidence flags. On the *Analyst* page, the 'Correlation vs Incremental Causal' table starkly highlights how comparing treated redeemers directly to control creates a +10.3 pp illusion of success due to selection bias, whereas the true Intention-to-Treat causal lift is +1.30 pp.
- Ran scripts/clean_clone_check.sh on the pushed repository: The script executed all 6 verification stages in an isolated temporary environment (clone, virtualenv setup, health check, full starter pipeline generation, pytest test suite, and git data diff check) and reported `OVERALL: PASS`, verifying bitwise identical data parity with zero uncommitted modifications.
- Other checks or changes I made: Manually queried the generated SQLite database (`churnexp.db`) in read-only mode to inspect foreign-key constraints and check clauses; verified that re-running `python -m churnexp all --scale starter` produces zero diff against committed starter data; required all financial and lift metrics to be represented in integer cents and synthetic currency units rather than dollar signs; and enforced that the agent never executes mutating git commands.

## Problems in AI output that I caught
1. Milestone 2: the agent reported 41 passing tests while my own run showed 2 failures, and it
   changed a schema CHECK to make a test pass. I had it revert the schema change and fix the test.
2. Milestone 2: the agent's report said documentation steps were done that were not on disk.
3. Run 3: the agent's pre-flight output showed git history that did not match my real history.
4. Run 2B / Run 3: The agent appended new ADRs using existing numbers (ADR-008 to ADR-011), colliding with the approved ADR numbering. I caught this and mandated renumbering them to ADR-013 through ADR-016 while preserving approved ADR-001 through ADR-012 intact.
5. Run 3: Empty-arm subgroups (OFF-2026-000003 at starter scale) initially generated an erroneous -100 pp lift; I caught this and directed the agent to output `null` in JSON and `'n/a (arm empty)'` in markdown, while adding `'small sample'` annotations for covariate checks with arm sizes under 200.
6. Run 3: The agent included raw '$' symbols in CLI evaluation summaries and reports; I caught this and required strict representation in integer cents and synthetic currency units.

## Prompt history
All prompts I sent to Claude and Antigravity are in ai-usage/prompts/, numbered in order, with the tool
name in each file name. AI responses are not included, except where noted. All 15 substantive prompt exchanges between Claude (as technical lead and architect) and Antigravity (as implementation agent) are preserved and documented in `ai-usage/prompts/` (files `001` through `015`). For initial brainstorming and brief clarification in Claude, prompt summaries capturing the exact architectural inputs and decision parameters were recorded in prompts 001 and 002.

## Limits of my own understanding
While I fully understand the end-to-end architecture, temporal snapshot design, randomized experiment design, eligibility rules, and business metrics, I would still study: (1) the mathematical derivation of the unpooled standard error formulas and Taylor-expansion approximations used for the ratio estimators in `src/churnexp/evaluation/lift.py` (specifically cost per incremental retained customer CI), and (2) the exact internal bit-generation mechanics of `numpy.random.SeedSequence` child stream derivation across multi-entity hierarchies.
