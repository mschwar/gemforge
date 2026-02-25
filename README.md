# GemForge — Your Personal AI Product Factory

One command turns any raw idea into a live, production-grade app.

## Usage

```bash
python gemforge_cli.py new "An ear training app that teaches pitch direction with pure tones"
```

When the vision is polished and ready, approve it:

```bash
python resume.py approve
# or request changes:
python resume.py refine "Make it more focused on beginners"
```

## The Pipeline

The full 13-agent factory runs automatically:

```
1.  Vision Polisher        → Sharpens your raw idea
2.  Human Review Gate      → You approve or refine
3.  Ruthless Interrogator  → Generates canonical docs
4.  Bootstrapper           → Creates real project folder + git repo
5.  UI/UX Agent            → Produces UIUX_SPEC.md
6.  Architecture Agent     → Produces ARCHITECTURE.md
    ┌─ 7. Frontend Agent ─┐
    ├─ 8. Backend Agent  ─┤ (parallel)
    └─ 9. Data Agent     ─┘
10. QA & Testing
11. Infrastructure
12. CI/CD
13. SRE & Observability
14. Deploy → Real Vercel URL
```

## Project Structure

```
gemforge/
├── agents/          # 13 premium agent prompt files
├── projects/        # Every gem gets its own folder + git repo
├── tools/           # file_tools.py, deploy_tools.py
├── state.py         # Shared PipelineState TypedDict
├── pipeline.py      # LangGraph pipeline definition
├── gemforge_cli.py  # Main launcher
├── resume.py        # Approval / refinement handler
├── main.py          # Alternative launcher
└── checkpoints.db   # Persists state across pauses (SqliteSaver)
```

## Requirements

- Python 3.12+
- Anthropic API key in `.env`
- Node.js + `npx vercel` for real deployment (optional)

```bash
pip install -r requirements.txt
```

---

Built with LangGraph + Claude. Made in 12 steps.
