# Via3 — IDE-First Agent Orchestrator

Via3 is the next iteration of the Via agent systems: a **production-shaped orchestrator** designed to solve software engineering tasks with **official-faithful validation** and a **human-in-the-loop** workflow (plan → diff → tests → approve).

This repo currently contains the Via2 codebase (ALO, Opus Orchestrator, Opus Meta-Orchestrator). The Via3 direction is specified in `PRD.md`.

## Goals (from `PRD.md`)

- **Evaluation rigor**: validation must match *official* SWE-bench behavior (e.g., function-level invocation when required).
- **Execution-guided selection**: generate **N patch candidates** (3–7), run real tests, select the best result.
- **Strong localization**: fast repo search (BM25/`rg`/stacktrace) + test-name → code mapping.
- **Human control**: show plan/logs/diff/tests; never auto-apply without explicit approval; support cancel/pause/resume.
- **Telemetry**: event-sourced logs + reproducible “artifact bundle” export (diff, logs, config, environment).

## Target architecture

```
┌──────────────────────────┐      HTTP / WebSocket      ┌──────────────────────────┐
│ IDE Extension / UI Client │  <──────────────────────>  │     Agent Service        │
│ (VS Code-class UX)        │                            │ (orchestrator + APIs)    │
└──────────────────────────┘                            └───────────┬──────────────┘
                                                                     │
                                                                     │
                                              ┌──────────────────────┴──────────────────────┐
                                              │                                             │
                                              ▼                                             ▼
                                   ┌──────────────────────┐                      ┌──────────────────────┐
                                   │    Sandbox Runner     │                      │     Model Gateway     │
                                   │ (local/Docker/remote) │                      │ (Anthropic/OpenAI/…) │
                                   └──────────────────────┘                      └──────────────────────┘
```

## Repo map (today)

- `alo/agentic_loops/`: core agent/orchestrator implementations (ALO + Opus family)
- `benchmark/`: SWE-bench runners, evaluators, analysis scripts
- `config/`: YAML configs for orchestrator variants
- `frontend/`: web UI prototype for the Opus Meta-Orchestrator (real-time logs via WebSocket)
- `docs/`: additional design notes

## Quick start (current code)

```bash
pip install -r requirements.txt
cp .env.example .env  # add your API keys
```

Run the Opus Orchestrator SWE-bench runner:

```bash
python benchmark/run_opus_agentic.py --num 5 --output results.jsonl
```

Run the Meta-Orchestrator web UI:

```bash
pip install -r frontend/requirements.txt
python frontend/app.py
```

## Creating a new orchestrator (Via3-style)

The Via3 orchestrator is intended to be an **Agent Service** with a stable API and pluggable internals (test adapters, sandbox backends, localization, model routing). Suggested development slices:

1. **Define the contract**
   - Request schema: issue/task + repo path + options (candidate count, budgets, adapters)
   - Streaming events: `status`, `test_result`, `patch_generated`, `final` (see `PRD.md` for an example shape)

2. **Implement validation-first execution**
   - Add a `SandboxRunner` abstraction (local subprocess vs Docker vs remote)
   - Add a `TestRunner` adapter layer (pytest, Django, …) with a single `run(target)` API

3. **Add multi-patch selection**
   - Generate N candidates under the same constraints/prompt
   - Execute the same validation procedure for each candidate
   - Select the best (pass rate, then cost/time, then patch size as a tie-breaker)

4. **Add localization as a first-class module**
   - `find_relevant_files(issue_text, error_text) -> ranked files`
   - `map_test_to_code(test_identifier) -> likely source locations`

5. **Make it reviewable**
   - Emit diffs without applying
   - Support apply/rollback semantics and artifact bundle export

If you want this README to become the root `README.md`, we can move the existing Via2 overview into a `docs/` file and keep the top-level focused on Via3.
