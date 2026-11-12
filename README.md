# GemForge

## TL;DR

Pass a plain-text app idea and optional `--context` folder to `gemforge new`. GemForge drafts product specs, pauses for your sign-off, copies a starter template, writes app code, runs tests, and outputs a ready-to-run repo with cost and deploy logs.

## Quick Start

Install the package in editable mode and start a new run:

```bash
pip install -e .
gemforge new "An ear training app that teaches pitch direction with pure tones"
```

Include existing source documents or code when extending a prior concept:

```bash
gemforge new "Add interval quizzes to the ear trainer" --context path/to/docs
```

GemForge pauses after drafting the product concept so you can approve or request changes before code generation runs:

```bash
gemforge resume approve
# or send refinement notes:
gemforge resume refine "Focus the first screen on beginner two-note intervals"
```

The standalone `python resume.py approve` and `python resume.py refine "..."` scripts remain supported for existing sessions.

Inspect projects, run event streams, build-cache state, and host prerequisites:

```bash
gemforge list
gemforge runs list
gemforge runs tail <run_id> --follow
gemforge build status <run_id>
gemforge doctor
```

## Test Commands

Run the zero-dependency documentation hygiene gate with system Python:

```bash
/usr/bin/python3 -m unittest tests/test_doc_hygiene.py -v
```

Run the full unit and integration suite from the repository root:

```bash
pytest -q
python -m pytest -q
```

## Pipeline Stages

Each run moves through 24 staged nodes with explicit state gates and SQLite checkpointing:

```text
0.  Document Auditor       -> Reads optional --context files into pipeline state
1.  Vision Polisher        -> Drafts a structured product concept from the raw idea
2.  Human Review Gate      -> Pauses until the operator approves or refines the concept
3.  Ruthless Interrogator  -> Writes brief, requirements, and application flow specs
4.  Bootstrapper           -> Creates the target project directory under PROJECTS_ROOT
5.  UI/UX Agent            -> Writes UIUX_SPEC.md
6.  Architecture Agent     -> Writes ARCHITECTURE.md
7.  Business Strategist    -> Writes BUSINESS_STRATEGY.md
8.  Landing Page Agent     -> Writes LANDING_PAGE.html
9.  Platform Decision      -> Writes PLATFORM_MANIFEST.md (Next.js, iOS, Android, Flutter, CLI)
10. Code Orchestrator      -> Applies platform template and dispatches specialist generators
    +-- 11. Frontend Agent
    +-- 12. Backend Agent   (parallel)
    +-- 13. Data Agent
14. QA Generator           -> Generates platform test suites
15. QA Runner              -> Executes xcodebuild, Jest, or pytest checks
16. Director Review        -> Verifies test results or routes back for repair/refinement
17. Infrastructure         -> Writes INFRA.md
18. CI/CD                  -> Writes .github/workflows/ci.yml and CICD.md
19. SRE and Observability  -> Writes SRE.md
20. Deploy                 -> Deploys web targets or records local native build status
21. Git Publish            -> Initializes Git repository and optional GitHub pull request
22. Shipping Manifest      -> Writes SHIPPING_MANIFEST.md
23. Weaver                 -> Records run lessons and updates user taste preferences
```

## Project Structure

```text
gemforge/
├── agents/          # Agent role specifications and versioned prompt templates
│   └── prompts/     # Versioned prompt files (metadata.json and v1.md)
├── core/
│   ├── build/       # Deterministic build graph, fingerprint cache, and taint registry
│   ├── discipline/  # Audit logging and cross-check enforcement
│   ├── evolution/   # Versioned prompt loader, iteration runner, and Weaver
│   ├── llm.py       # Shared model client and token-cost wrapper
│   ├── memory/      # SQLite lessons store, semantic index, and taste preferences
│   ├── pipeline_stages/ # Stage nodes, context builders, and failure envelopes
│   ├── prediction/  # Candidate idea scoring helpers
│   ├── repair/      # Failure signature extraction and bounded repair loop
│   ├── reporting/   # Project fleet and cumulative cost queries
│   ├── runtime/     # Event bus, outbox store, reducer, and worker daemons
│   ├── shipping/    # Launch manifest writer
│   └── swarm/       # Specialist agent spawner
├── src/gemforge/    # CLI entrypoint (gemforge new, resume, list, runs, build, doctor)
├── tools/           # File, execution, Git, deployment, and cost tracking utilities
├── templates/       # Project templates (Next.js, iOS SwiftUI, Android Kotlin, Flutter, CLI)
├── state.py         # PipelineState TypedDict contract
├── pipeline.py      # LangGraph state graph builder
├── resume.py        # Standalone human-review resume helper
└── dashboard.py     # Streamlit run and cost dashboard
```

## Architecture and Guides

- Agent operating contract: [AGENTS.md](AGENTS.md)
- Stage ownership and state gates: [docs/architecture/PIPELINE_STAGE_MAP.md](docs/architecture/PIPELINE_STAGE_MAP.md)
- Prompt evolution protocol: [docs/v2.0/EVOLUTION_DISCIPLINE_PROTOCOL.md](docs/v2.0/EVOLUTION_DISCIPLINE_PROTOCOL.md)
- Runtime and memory blueprints:
  - [Blueprint 01: Event-Driven Forge Runtime](docs/blueprints/BLUEPRINT_01_EVENT_DRIVEN_FORGE_RUNTIME.md)
  - [Blueprint 02: Semantic Memory and Agentic Repair Loop](docs/blueprints/BLUEPRINT_02_SEMANTIC_MEMORY_AGENTIC_REPAIR_LOOP.md)
  - [Blueprint 03: Deterministic Build Graph and Incremental Cache](docs/blueprints/BLUEPRINT_03_DETERMINISTIC_BUILD_GRAPH_INCREMENTAL_CACHE.md)
  - [Horizon 1: Distributed Execution Fabric](docs/blueprints/horizon_1/H1_DISTRIBUTED_FABRIC.md)
  - [Horizon 2: Semantic Immune System](docs/blueprints/horizon_2/H2_SEMANTIC_IMMUNE_SYSTEM.md)
  - [Horizon 3: Meta-Evolution Daemon](docs/blueprints/horizon_3/H3_META_EVOLUTION_DAEMON.md)

## Requirements

- Python 3.12+
- `ANTHROPIC_API_KEY` set in `.env` or exported in the shell environment
- Node.js and `npx vercel` for optional web deployments
- Xcode and `xcodegen` on macOS for optional iOS builds

```bash
pip install -r requirements.txt
# or
pip install -e .
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | None | Anthropic API key used by pipeline model calls |
| `PROJECTS_ROOT` | No | `../gemforge-projects` | Output directory where generated projects are written |
| `GEMFORGE_AUTO_PUSH` | No | `false` | Push generated repositories to GitHub during publish |
| `GEMFORGE_COMMIT_FACTORY_ROOT` | No | `false` | Commit factory metadata updates after a completed run |

## Cost Tracking

Each invocation prints session token counts, call counts, and cumulative spend stored in `checkpoints.db`:

```text
Session: $0.0124 | Tokens: 49,200 | Calls: 23
All-time total: $0.3847
```

Launch the local cost and project history dashboard with:

```bash
streamlit run dashboard.py
```
