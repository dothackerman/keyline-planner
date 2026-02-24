---
name: self-improvement-codex-copilot
description: Capture errors, corrections, and repeatable improvements for continuous agent quality. Use when commands fail, users correct outputs, tooling/integration issues appear, or better recurring patterns are discovered. Designed for OpenAI Codex and GitHub Copilot Agent workflows.
---

# Self-Improvement (Codex + Copilot Agent)

Log high-signal learnings in-repo so future agent runs improve behavior and reliability.

## When to use

Use this skill immediately when any of the following happens:

- A command/tool call fails unexpectedly
- The user corrects the agent’s output or assumptions
- A requested capability is missing
- An API/integration behaves differently than expected
- A repeatable better approach is discovered

## Quick actions

| Situation | Log file |
|---|---|
| Command/tool failure | `.learnings/ERRORS.md` |
| Correction or better practice | `.learnings/LEARNINGS.md` |
| Missing capability request | `.learnings/FEATURE_REQUESTS.md` |

Also promote stable, broadly useful rules to:

- `AGENTS.md` for workflow/process rules
- `.github/copilot-instructions.md` for Copilot-specific guidance (create if needed)
- `README.md` (or project docs) for user-facing behavior

## Minimal setup

```bash
mkdir -p .learnings
touch .learnings/LEARNINGS.md
touch .learnings/ERRORS.md
touch .learnings/FEATURE_REQUESTS.md
```

## Entry templates

### 1) Learning (`.learnings/LEARNINGS.md`)

```markdown
## [LRN-YYYYMMDD-001] short-title

**Logged**: 2026-01-01T12:00:00Z
**Priority**: low | medium | high
**Status**: pending
**Area**: docs | code | tests | tooling | workflow

### Summary
One-line learning.

### Details
What was wrong, what is now known to be correct, and why.

### Suggested Action
Concrete update to implement or enforce.

### Metadata
- Source: user_feedback | runtime_error | review
- Related Files: path/to/file
- Tags: tag1, tag2
```

### 2) Error (`.learnings/ERRORS.md`)

```markdown
## [ERR-YYYYMMDD-001] command-or-tool

**Logged**: 2026-01-01T12:00:00Z
**Priority**: medium | high
**Status**: pending
**Area**: docs | code | tests | tooling | workflow

### Summary
What failed.

### Error Output

    Paste the exact error output here (indented block).

### Context
Command/action attempted, parameters, and environment details.

### Suggested Fix
Likely remediation.

### Metadata
- Reproducible: yes | no | unknown
- Related Files: path/to/file
```

### 3) Feature request (`.learnings/FEATURE_REQUESTS.md`)

```markdown
## [FEAT-YYYYMMDD-001] capability-name

**Logged**: 2026-01-01T12:00:00Z
**Priority**: low | medium | high
**Status**: pending
**Area**: docs | code | tests | tooling | workflow

### Requested Capability
What was requested.

### User Context
Why it is needed.

### Suggested Implementation
Practical first implementation path.

### Metadata
- Frequency: first_time | recurring
- Related Features: existing-feature
```

## Operational rules for Codex/Copilot Agent

1. Keep entries concise and factual; include exact failed command/output for errors.
2. Prefer one issue per entry for easy triage and automation.
3. When fixed, update `Status` to `resolved` and add:
   - resolution date
   - commit SHA / PR reference
   - short note of the applied fix
4. If the same issue repeats, link prior IDs instead of duplicating context.
5. Promote only durable guidance to agent instruction files; keep transient noise in `.learnings/`.

## ID format

`TYPE-YYYYMMDD-###`

- `TYPE`: `LRN`, `ERR`, `FEAT`
- Date in UTC (`YYYYMMDD` format)
- 3-digit counter per day/file

Example: `ERR-20250115-003`
