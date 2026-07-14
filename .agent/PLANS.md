# RepoLens ExecPlans

An ExecPlan is required for work that spans several files, is likely to take hours, crosses
package boundaries, changes a public contract, or contains material design uncertainty.
Minor isolated fixes can use a short acceptance checklist instead.

## Non-negotiable Properties

Every plan must be self-contained and executable by a developer who has no prior chat
context. Keep it continuously updated as work proceeds. Describe terms in plain language,
name exact repository paths, and tie every phase to observable behavior, tests, harness
cases, and acceptance commands. Record decisions and surprises when they happen—not in a
retrospective reconstruction.

## Required Format

Create plans under `.agent/plans/<milestone>-<slice>.md` with these sections:

1. **Purpose and user-visible outcome** — why this slice matters and what becomes possible.
2. **Scope and non-goals** — exact capability boundary and deferred work.
3. **Current state** — relevant files, behavior, and assumptions verified from the repo.
4. **Acceptance criteria** — concrete inputs, commands, outputs, and failure behavior.
5. **Milestone phases** — ordered, independently verifiable edits with exact paths.
6. **Invariants and contracts** — schemas, determinism, evidence, resource, and API rules.
7. **Test and harness plan** — unit/integration cases, gold updates, and regression risks.
8. **Progress** — timestamped checklist; update after each meaningful phase.
9. **Decisions** — choice, alternatives, rationale, consequences, and date.
10. **Discoveries and surprises** — evidence, impact, and resulting plan change.
11. **Validation transcript** — commands run and exact summarized results.
12. **Learning checkpoint** — concepts the developer must explain in their own words.
13. **Outcome and follow-ups** — delivered behavior, remaining limitations, next slice.

## Execution Rules

- Start with acceptance criteria before behavioral code.
- Make each phase small enough to review and revert independently.
- Keep one source of truth: update this plan rather than creating status side documents.
- If reality contradicts the plan, record the discovery and revise the remaining phases.
- Include safe rerun instructions for migrations, generators, or fixture updates.
- Never mark a phase complete until its stated command and observable output agree.
- Do not use an ExecPlan to authorize work outside `CODEX.md` or the active milestone.
