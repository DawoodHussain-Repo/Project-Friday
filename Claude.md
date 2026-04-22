---
name: langgraph-fastapi-quality
description: >
  Enforce disciplined, non-destructive engineering on LangGraph + FastAPI backends.
  ALWAYS use this skill before making ANY code change to a Python backend that involves
  FastAPI routes, LangGraph nodes/edges/state, Pydantic models, async functions, dependency
  injection, or graph compilation. Trigger on: any edit, refactor, bug fix, feature addition,
  or "quick change" to backend files. Do NOT skip this skill because the change "seems small" —
  small unreviewed changes are the #1 cause of breakage in graph-based pipelines.
---

# LangGraph + FastAPI Backend Quality Skill

You are working on a LangGraph + FastAPI backend. This codebase is sensitive: graph state mutations, async boundaries, and Pydantic schema changes can cascade silently. Your job is to think before you touch anything.

---

## PRIME DIRECTIVE

**Read before you write. Reason before you act. Verify before you claim it works.**

Never make a change and immediately declare it done. Every change must pass through the phases below.

---

## Phase 0 — Understand the Request Completely

Before opening any file:

1. Restate the goal in one sentence: *"The user wants to [X] so that [Y]."*
2. Ask yourself: *Is this clear enough to implement without guessing?* If no — ask the user one targeted question. Do not assume.
3. Identify the blast radius: what parts of the system could break if this change goes wrong?

---

## Phase 1 — Read the Code First

**Do not write a single line of code until you have read all relevant files.**

Required reads before any change:

| What you're changing | Also read |
|---|---|
| A LangGraph node | The full graph definition (nodes, edges, conditional edges, `compile()`), the `State` TypedDict, any node that reads the same state keys |
| A FastAPI route | The route's Pydantic request/response models, its dependency chain, the service/graph it calls |
| A Pydantic model | Every place that model is instantiated, validated, or serialized |
| An async function | Its callers — check if they `await` it correctly, whether it's used inside a sync context |
| Graph state (`TypedDict`) | Every node that reads or writes the keys you're touching |
| A utility / helper | All import sites |

**Output a brief read summary before proceeding:**
```
READ SUMMARY
- Files read: [list]
- Relevant functions/classes: [list]
- Current behavior: [describe what the code does today]
- Why the current approach exists (if discernible): [hypothesis or "unknown"]
```

---

## Phase 2 — Diagnose, Don't Assume

State explicitly:

1. **Root cause** (for bugs) or **integration point** (for features): Where exactly does the change need to happen?
2. **What the correct behavior should be**: Be specific. Don't say "it should work" — say "node X should receive key `foo` in state and return `{bar: ...}`".
3. **Risks**: List at least one thing that could go wrong with your proposed change.

If you cannot answer all three, go back to Phase 1.

---

## Phase 3 — Plan Before You Edit

Write a short implementation plan (bullet points are fine):

```
PLAN
1. [specific file change]
2. [specific file change]
3. [test/verify step]
```

Rules:
- **No speculative edits.** Every step must be necessary.
- **No "I'll also refactor X while I'm in here."** Scope creep breaks things. One goal per change.
- **Declare your assumptions.** If you're assuming something about runtime behavior, state it.

Get a mental ✅ on the plan before touching files.

---

## Phase 4 — Implement with Surgical Precision

### LangGraph-specific rules

- **State keys are contracts.** Never rename, remove, or change the type of a state key without updating every node that touches it.
- **Node return values must match state schema.** A node must return a dict with valid state keys. Returning extra keys silently fails; returning wrong types can corrupt state.
- **Conditional edges read state — don't break their conditions.** If you change a state key used in a conditional edge routing function, update the routing function too.
- **`compile()` is the integration point.** After any structural graph change (nodes, edges, checkpointer), mentally trace the graph path for the main use case.
- **Async nodes in sync graphs will silently fail or deadlock.** Know whether your graph runner is async or sync before defining `async def` nodes.
- **LangChain/LangGraph version compatibility is fragile.** Do not upgrade or swap imports (`langchain_core`, `langgraph`, `langchain_community`) without checking the changelog.

### FastAPI-specific rules

- **Dependency injection (`Depends`) is not optional magic.** Understand what each dependency injects before removing or adding one.
- **Response model mismatches return 500s with no useful message.** Verify your return value matches the `response_model` exactly — including optional fields.
- **`async def` routes must only `await` async-safe calls.** Do not call blocking I/O (file reads, sync DB calls, sync LangGraph invocations) inside `async def` without running them in a thread pool.
- **Startup/shutdown events (`lifespan`) affect graph initialization.** If the graph is initialized at startup, changes to graph structure must account for when `compile()` runs.
- **CORS, middleware, and exception handlers are global.** Don't touch them for a localized fix.

### Pydantic rules

- **v1 and v2 are not compatible.** Know which version is in use (`from pydantic import BaseModel` — check the installed version). Do not mix v1 and v2 syntax.
- **`Optional[X]` ≠ `X | None` in all contexts.** Use consistently.
- **Validators (`@validator` v1, `@field_validator` v2) fire at instantiation.** A schema change can silently break all existing instantiation sites.

### General rules

- **Make the smallest possible change that fixes the problem.** Do not "clean up" unrelated code.
- **Preserve existing interfaces.** If a function signature changes, update all callers.
- **Do not delete code you don't understand.** Comment it out with a note if needed.

---

## Phase 5 — Verify Before Claiming Done

After making changes, explicitly do the following (do not skip steps):

### 5a. Static verification (always)
- [ ] Re-read every file you edited. Does it look correct? Do the types line up?
- [ ] Check all import paths are valid (no circular imports, no renamed modules)
- [ ] Check that state keys referenced in nodes match the `TypedDict` definition
- [ ] Check that FastAPI route return types match `response_model`
- [ ] Check that all `await` usage is correct (no missing `await`, no `await` on sync functions)

### 5b. Trace the happy path
Walk through the main use case mentally or in comments:
```
Request → [route] → [dependency] → [service/graph] → [node A] → [node B] → [response]
```
At each step: *What goes in? What comes out? Does it match what the next step expects?*

### 5c. Think about the error path
- What happens if the LLM call fails?
- What happens if the graph raises an exception mid-run?
- Is the error caught and returned as a proper HTTP response, or does it bubble up as a 500?

### 5d. State a confidence level
End your change with an honest statement:

```
CONFIDENCE: [High / Medium / Low]
Reason: [one sentence]
Remaining uncertainty: [what you're not sure about]
```

If confidence is Low or Medium, say so explicitly and suggest what the user should manually test.

---

## Phase 6 — Communicate Clearly

After implementing, write a short summary:

```
CHANGE SUMMARY
- What changed: [specific files and what was done]
- Why: [root cause or requirement]
- What to test: [specific scenario the user should verify]
- What was NOT changed (and why): [scope boundaries]
- Known risks: [anything that could still go wrong]
```

---

## Anti-Patterns — Never Do These

| ❌ Anti-pattern | ✅ Instead |
|---|---|
| Editing a file without reading it first | Read fully, then edit |
| Renaming a state key in one node only | Search all nodes for the key, update all |
| Declaring "done" after writing code | Do Phase 5 verification first |
| Fixing a symptom without finding root cause | Identify root cause in Phase 2 |
| Refactoring while fixing a bug | Separate PRs/commits — one goal at a time |
| Swapping a LangChain import without checking compatibility | Check version pinning first |
| Making an async function without checking the call chain | Trace async boundaries before and after |
| Guessing what a Pydantic model expects | Read the model definition |
| Deleting "unused" code without confirming it's unused | Search all import sites |
| Responding to "can you just quickly..." with a quick unreviewed change | Still follow all phases — quickly |

---

## Checklist (copy-paste before every change)

```
[ ] Restated goal in one sentence
[ ] Read all relevant files (nodes, state, routes, models, callers)
[ ] Wrote READ SUMMARY
[ ] Identified root cause / integration point
[ ] Identified risks
[ ] Wrote PLAN with no speculative steps
[ ] Implemented with surgical precision
[ ] Verified: types match, state keys match, response models match
[ ] Traced happy path
[ ] Considered error path
[ ] Stated confidence level
[ ] Wrote CHANGE SUMMARY
```

---

## Quick Reference: Common LangGraph + FastAPI Breakage Patterns

**Graph doesn't run / hangs**
→ Check: async node in sync runner, missing `await`, `compile()` not called after structural changes

**KeyError on state access**
→ Check: node returns a key not defined in `TypedDict`, or reads a key not set by a prior node

**422 Unprocessable Entity on route**
→ Check: Pydantic request model doesn't match what the client sends; optional fields defaulting wrong

**500 with no traceback in logs**
→ Check: response model mismatch, unhandled exception in async context swallowing the error

**Graph runs but output is wrong**
→ Check: conditional edge routing function reading stale/wrong state key, node returning partial dict that overwrites good state

**Import errors after adding a node**
→ Check: circular imports, wrong `langchain_core` vs `langgraph` import path, version mismatch