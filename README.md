# GemForge — Your Personal AI Product Factory

One command turns any raw idea into a live, production-grade app.

## Quick Start

```bash
pip install -e .
gemforge new "An ear training app that teaches pitch direction with pure tones"
```

When the vision is polished and ready (the pipeline pauses and prints it), approve or refine:

```bash
python resume.py approve
# or request changes:
python resume.py refine "Make it more focused on beginners"
```

List your forged projects:

```bash
gemforge list
```

## The Pipeline

The full 24-node factory runs automatically:

```
0.  Document Auditor       → Ingests existing docs/code (optional --context)
1.  Vision Polisher        → Sharpens your raw idea into a crisp concept
2.  Human Review Gate      → ⏸️  You approve or refine before anything is built
3.  Ruthless Interrogator  → Generates canonical docs (brief, PRD, app flow)
4.  Bootstrapper           → Creates real project folder
5.  UI/UX Agent            → UIUX_SPEC.md
6.  Architecture Agent     → ARCHITECTURE.md
7.  Business Strategist    → BUSINESS_STRATEGY.md
8.  Landing Page Agent     → LANDING_PAGE.html
9.  Platform Decision      → PLATFORM_MANIFEST.md (iOS / web / Flutter / etc.)
10. Code Orchestrator      → Applies template + boots specialist agents
    ┌─ 11. Frontend Agent ─┐
    ├─ 12. Backend Agent  ─┤  (parallel)
    └─ 13. Data Agent     ─┘
14. QA Generator           → Writes tests
15. QA Runner              → xcodebuild / Jest
16. Director Review        → Approves build or loops back (max 3 rejections)
17. Infrastructure         → INFRA.md
18. CI/CD                  → .github/workflows/ci.yml + CICD.md
19. SRE & Observability    → SRE.md
20. Deploy                 → Vercel URL (web) or skipped (native)
21. Git Publish            → GitHub repo + PR
22. Shipping Manifest      → SHIPPING_MANIFEST.md
23. Weaver                 → Extracts lessons; updates taste model for future runs
```

## Project Structure

```
gemforge/
├── agents/          # 28 premium agent prompt files
│   └── prompts/     # Versioned prompts (metadata.json + v1.md per agent)
├── core/
│   ├── discipline/  # DisciplineEnforcer — audit log, optional auto-commit
│   ├── evolution/   # PromptLoader (versioned), IterationEngine, Weaver
│   ├── llm.py       # Shared LLM client + cost_aware_invoke (no circular deps)
│   ├── memory/      # LessonsManager (SQLite) + UserTasteManager (JSON)
│   ├── prediction/  # Oracle — predictive idea engine
│   ├── reporting/   # EmpireStats — project fleet + cost history
│   ├── shipping/    # Shipper — launch manifest generator
│   └── swarm/       # SwarmFactory — dynamic specialist agent spawner
├── src/gemforge/    # Installed CLI package
│   └── cli.py       # gemforge new / gemforge list
├── tools/           # file_tools, deploy_tools, executor_tools, cost_tracker, git_tools
├── templates/       # App scaffolding templates (iOS, Next.js, Flutter, etc.)
├── state.py         # PipelineState TypedDict — single source of truth
├── pipeline.py      # LangGraph pipeline (get_pipeline_app — lazy build)
├── resume.py        # Approval / refinement handler
├── main.py          # Legacy launcher (python main.py "idea")
├── iterate.py       # Post-forge code surgery tool
├── dashboard.py     # Streamlit empire stats dashboard
└── checkpoints.db   # Persists state across pauses (SqliteSaver)
```

## Requirements

- Python 3.12+
- `ANTHROPIC_API_KEY` in `.env` (or exported)
- Node.js + `npx vercel` for web deployment (optional)
- Xcode for iOS builds (optional)

```bash
pip install -r requirements.txt
# or
pip install -e .
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — | Anthropic API key |
| `PROJECTS_ROOT` | No | `../gemforge-projects` | Where generated projects are saved |
| `GEMFORGE_AUTO_PUSH` | No | `false` | Push generated project to GitHub after forge |
| `GEMFORGE_COMMIT_FACTORY_ROOT` | No | `false` | Auto-commit the factory repo on each run |

## Cost Tracking

Every run shows:

```
💰 Session: $0.0124 | Tokens: 49,200 | Calls: 23
📊 All-time total: $0.3847
```

Cost is persisted to `checkpoints.db` across sessions. View totals in the dashboard:

```bash
streamlit run dashboard.py
```

---

Built with LangGraph + Claude 3 Haiku.
