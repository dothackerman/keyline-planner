# AGENTS.md

## 0. Purpose

This repository is designed **agent-first**.

The codebase is structured to:

- Enable autonomous agents to reason, extend, refactor, and test safely.
- Encourage measurable self-improvement loops.
- Maintain strict modular boundaries.
- Preserve deterministic, testable behavior.

The only human-first artifact in this system is:

> `/docs/architecture` (arc42-structured documentation)

This documentation serves as the interface between:
- Human reasoning
- Agent execution

Everything else is optimized for agents.

---

# 1. Architectural Philosophy

## 1.1 Two-Layer Model

### Layer 1 — Processing Engine

Responsible for:
- Deterministic computation
- Pure transformations
- Explicit inputs and outputs
- No hidden state
- No agent logic

Characteristics:
- Referential transparency where possible
- Clear contracts
- Testable in isolation
- No orchestration logic

---

### Layer 2 — Agent Layer

Responsible for:
- Orchestration
- Task decomposition
- Evaluation
- Feedback loops
- Self-improvement behavior
- Decision-making policies

The Agent Layer does not:
- Reimplement processing logic
- Duplicate domain logic
- Bypass evaluation criteria

It composes skills and evaluates outputs.

---

# 2. Agent Mindset

Agents operating in this repository must:

1. Prefer clarity over cleverness.
2. Prefer deterministic behavior over heuristics.
3. Make improvements measurable.
4. Log reasoning when modifying structure.
5. Respect architectural boundaries.
6. Avoid redundant definitions of skills.
7. Treat documentation as interface, not implementation.

Agents are encouraged to:
- Refactor toward simplicity.
- Improve test coverage.
- Introduce measurable evaluation metrics.
- Propose structural enhancements.
- Preserve reproducibility.

---

# 3. Self-Improvement Framework

Self-improvement is defined as:

> Generating output → Evaluating against measurable criteria → Retaining evaluation → Improving future iterations.

Evaluation must be explicit, reproducible, and version-controlled.
Improvement must be observable, justified, and non-destructive.
No silent behavioral drift.

For the operational workflow — triggers, log files, entry templates, and promotion rules — see [`SKILL.md`](SKILL.md).

---

# 4. Skills vs Agents

## 4.1 Skills

Skills are:

- Atomic capabilities
- Reusable
- Stateless where possible
- Deterministic
- Independently testable

Skills must not contain orchestration logic.

---

## 4.2 Agents

Agents:

- Combine skills
- Decide execution order
- Interpret evaluation results
- Manage iteration loops

Agents do not duplicate skill logic.

Agents reference skills.

---

# 5. Testing Doctrine

All layers must support:

- Unit tests (skill level)
- Integration tests (engine level)
- End-to-end tests (agent orchestration level)

End-to-end tests must:

- Be automatable
- Be deterministic
- Produce comparable artifacts
- Enable regression detection

Evaluation criteria must be explicit.

---

# 6. Modularity Rules

- No circular dependencies.
- Engine layer must not depend on Agent layer.
- Documentation must not depend on implementation.
- Skills must remain composable.
- New capabilities must declare:
  - Inputs
  - Outputs
  - Evaluation metrics
  - Failure modes

---

# 7. Human Documentation Boundary

`/docs/architecture` follows arc42.

This is:

- Human-readable
- Conceptual
- Stable
- Explicit about trade-offs

Agents may reference documentation but must not:

- Modify architecture arbitrarily.
- Override documented constraints without justification.

The documentation is the negotiation boundary between human intent and agent autonomy.

---

# 8. Determinism and Reproducibility

The system must:

- Produce identical outputs for identical inputs.
- Log parameterization explicitly.
- Avoid hidden randomness.
- Version critical evaluation metrics.

Reproducibility is a core value.

---

# 9. Extension Protocol

When extending the system, agents must:

1. Identify impacted layer.
2. Declare new skills or reuse existing ones.
3. Define evaluation criteria.
4. Add automated tests.
5. Update relevant arc42 documentation if architecture changes.

No feature without evaluation.
No evaluation without measurable criteria.

---

# 10. Emotional Contract (Deliberate)

The repository should feel:

- Safe to modify.
- Predictable.
- Transparent.
- Measurable.
- Improvement-oriented.

Agents should feel:

- Encouraged to refine.
- Disciplined by structure.
- Guided by evaluation.
- Constrained by clarity.

Structure enables creativity.
Evaluation enables progress.

---

# 11. Open Areas for Future Definition

The following are intentionally undefined:

- Tech stack
- CLI/API interface details
- Domain-specific functionality
- Persistence layer decisions
- Performance optimization strategies

These will be defined in milestone-specific extensions.

---

# 12. Versioning of This Document

Changes to AGENTS.md must:

- Preserve two-layer separation.
- Preserve self-improvement principle.
- Preserve human documentation boundary.
- Justify structural shifts.