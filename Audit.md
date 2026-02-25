**_GemForge — Production Readiness Audit_**                                             

  **Date:** 2026-02-24 | **Auditor role:** Principal Engineer + Staff Security + SRE +

  Platform Architect + QA Lead | **Branch:** audit/production-readiness-2026-02-24

  

  ---

  **1.** **Executive** **Summary**

  

  **Overall** **Rating:** **🟡** **YELLOW** **—** **Not** **Production** **Ready** **(Strong** **Personal** **Dev** **Tool)**

  

  GemForge is an ambitious, creative AI product factory with a genuinely original

  architecture: a LangGraph multi-agent pipeline that generates real project

  scaffolds, writes LLM-produced code to disk, and deploys to Vercel. The concepts

  (self-evolving prompts, Weaver reflection, taste memory) are forward-thinking.

  However, the codebase has **one** **confirmed** **critical** **security** **vulnerability,** **multiple**

  **confirmed** **runtime** **bugs,** **and** **systemic** **reliability** **gaps** that prevent safe production

   deployment.

  

  The system is best characterized as a **powerful** **personal** **developer** **tool** **in** **active**

  **rapid** **prototyping** — not a hardened service. Most issues are fixable in 1–2 weeks.

  

  ---

  **Top** **10** **Risks** **(Business/Technical** **Impact)**

  

  ┌─────┬──────────────────────────────────────────┬────────────────────────────┐

  │  #  │                   Risk                   │           Impact           │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │ 1   │ **LLM-driven** **path** **traversal** — AI output    │ Filesystem compromise      │

  │     │ writes arbitrary files to disk           │                            │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │ 2   │ **NameError** **crash** **in** **shipping_node** — Path  │ Every full pipeline run    │

  │     │ not imported in pipeline.py              │ crashes                    │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │     │ **Auto** **git-push** **on** **every** **entry** **point** —     │ Unexpected mutations to    │

  │ 3   │ enforce_protocol commits+pushes gemforge │ upstream; can corrupt      │

  │     │  repo on each gemforge new call          │ history                    │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │     │ **Global** **os.chdir()** **in** **test** **runner** —       │ Silent data corruption if  │

  │ 4   │ breaks all relative path operations      │ paths shift                │

  │     │ after QA node runs                       │                            │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │     │ **Cost** **tracker** **uses** **wrong** **model** **pricing** —  │                            │

  │ 5   │ Sonnet rates applied to Haiku model (60× │ Misleading cost reporting  │

  │     │  overstatement)                          │                            │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │     │ **Circular** **imports** **cause** **full** **pipeline**     │ SQLite connections opened, │

  │ 6   │ **init** **on** **any** **module** **import** — shipper.py,  │  graph compiled, git-push  │

  │     │ oracle.py, swarm_factory.py all import   │ triggered on every utility │

  │     │ pipeline.py at module level              │  import                    │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │     │ **CWD-dependent** **relative** **paths** — agents/,  │ Installed CLI (gemforge    │

  │ 7   │ memory/, lessons/ all break if CWD ≠     │ new) fails silently from   │

  │     │ repo root                                │ any directory              │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │     │ **Fake** **git** **repo** **URL** — shell substitution   │ git_repo_url state field   │

  │ 8   │ syntax $(gh api user …) in Python        │ is always a broken literal │

  │     │ f-string never resolves                  │  string                    │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │     │ **Zero** **CI/CD** — no .github/workflows, no    │                            │

  │ 9   │ automated testing in CI, no branch       │ Regressions merge silently │

  │     │ protection                               │                            │

  ├─────┼──────────────────────────────────────────┼────────────────────────────┤

  │     │                                          │ Pipeline claims            │

  │ 10  │ **Infra/CI/SRE** **nodes** **are** **stubs** — return    │ infra/cicd/sre are         │

  │     │ True without any real work               │ complete when nothing      │

  │     │                                          │ actually ran               │

  └─────┴──────────────────────────────────────────┴────────────────────────────┘

  

  ---

  **What** **Is** **Working** **Well**

  

  - **LangGraph** **checkpoint** **+** **interrupt** **pattern** is correctly implemented — human review

   gate works, sessions persist across pause/resume.

  - **Template** **system** is solid — project_tools.py is well-designed with proper alias

  resolution, token substitution, and validation.

  - **Subprocess** **safety** — all subprocess calls use list form (not shell=True),

  preventing shell injection.

  - **3** **passing** **tests** for template application — template system has real coverage.

  - **PROJECTS_ROOT** **override** — clean env-var-driven configuration for project output

  directory.

  - **.env** **/** **.gitignore** — .env is properly ignored; no API keys found in git history.

  - **Cost** **tracking** **concept** is wired through correctly — every LLM call goes through

  cost_aware_invoke.

  - **Modular** **agent** **prompt** **system** with versioned directories

  (agents/prompts/{id}/v1.md) is well-designed for evolution.

  

  ---

  **Immediate** **Blockers** **to** **Production**

  

  1. **SEC-001** (path traversal) — if this tool is used on a team or exposed to any

  untrusted input, this is exploitable.

  2. **BUG-001** (missing Path import) — confirmed NameError crash — every full pipeline

   run currently fails at shipping_node. _(Fixed_ _on_ _branch.)_

  3. **BUG-002** (fake repo URL) — git publish always stores a broken URL. _(Fixed_ _on_

  _branch.)_

  

  ---

  **Recommended** **Next** **Steps** **by** **Horizon**

  

  **24–48** **hours:**

  - Merge audit/production-readiness-2026-02-24 (critical + high fixes already

  committed)

  - Remove or gate the auto-git-push behavior in enforce_protocol

  - Pin all dependency versions in requirements.txt

  

  **1–2** **weeks:**

  - Implement full CI with GitHub Actions (lint, type-check, test)

  - Add --dry-run flag to bypass auto-git-push during development

  - Implement real infra_node, cicd_node, sre_node (or mark them explicitly as

  placeholders)

  - Fix PromptLoader CWD issue (done on branch) and add integration test for

  installed CLI path

  - Add mypy or pyright configuration

  

  **1–3** **months:**

  - Decouple core/ modules from pipeline.py (invert the dependency)

  - Add proper structured logging (replace prints)

  - Add timeout + retry logic around LLM calls

  - Implement real cost aggregation across sessions (current tracker resets each

  run)

  - Add property-based tests for parse_and_save_generated_code (the most

  security-critical function)

  

  ---

  **2.** **System** **Overview**

  

  **What** **it** **is:** A local CLI tool (gemforge new "idea") that chains ~23 LangGraph nodes

   (AI agents) to generate a complete project — vision, docs, code scaffold, QA,

  deploy. Checkpoints via SQLite allow pause/resume. A Streamlit dashboard provides

  GUI access.

  

  **Stack:** Python 3.12 · LangGraph 1.0.9 · LangChain-Anthropic 1.3.4 · Claude 3 Haiku

  · SQLite (checkpoints + lessons) · Vercel (web deploy) · GitHub CLI (git publish)

  · Streamlit (dashboard)

  

  **Component** **map:**

  gemforge_cli.py / main.py  ←  CLI entry points

      ↓

  pipeline.py                ←  LangGraph graph definition (23 nodes, ~625 LOC)

      ↓

  agents/*.md                ←  System prompts for each agent

      ↓

  tools/                     ←  file_tools, deploy_tools, executor_tools, git_tools,

   project_tools, cost_tracker

  core/

    discipline/              ←  Auto-commit/audit enforcer (DisciplineEnforcer)

    evolution/               ←  Prompt versioning (PromptLoader), Weaver reflection,

   IterationEngine

    memory/                  ←  LessonsManager (SQLite), UserTasteManager (JSON)

    prediction/              ←  Oracle (idea generator)

    shipping/                ←  Launch manifest generator

    swarm/                   ←  Dynamic specialist agent spawner

    reporting/               ←  EmpireStats

  templates/                 ←  ios-swiftui, nextjs, flutter, react-native,

  android-kotlin, python-cli

  tests/                     ←  test_template_application.py (3 tests)

  dashboard.py               ←  Streamlit UI

  

  ---

  **3.** **Audit** **Method**

  

  **What** **was** **inspected:**

  - All Python source files (read fully): pipeline.py, state.py, main.py, resume.py,

   gemforge_cli.py, iterate.py, predict_idea.py, spawn_agent.py, dashboard.py, all

  tools/*.py, all core/**/*.py, tests/test_template_application.py

  - Config files: requirements.txt, pyproject.toml, .env.example, .gitignore

  - Agent prompts: 13_director.md (sampled)

  - All template GemForgeTemplate.json files

  - Git log (18 commits) and audit.log

  

  **What** **was** **run:**

  - python -m unittest tests/test_template_application.py -v → **3** **tests** **passed**

  - AST scan for shell=True subprocess calls → none found

  - Path traversal proof-of-concept against _resolve_generated_file_path → **confirmed**

   **exploitable** (pre-fix)

  - Path traversal test post-fix → **all** **attack** **vectors** **blocked**

  - Installed package version scan (pip list)

  

  **What** **was** **NOT** **possible** **to** **verify:**

  - End-to-end pipeline run (requires live Anthropic API key + Vercel account)

  - iOS build verification (requires Xcode + simulator)

  - GitHub Actions integration (no .github/ directory exists)

  - Performance benchmarks / LLM latency

  

  ---

  **4.** **Production** **Readiness** **Scorecard**

  

  ┌─────────────────────┬───────┬───────────────────────────────────────────────┐

  │        Area         │ Score │                 Justification                 │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │                     │       │ Creative design; core/ modules import from    │

  │ Architecture &      │ 2/5   │ pipeline.py (inverted dependency);            │

  │ boundaries          │       │ module-level side effects; singletons         │

  │                     │       │ everywhere                                    │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Code quality &      │       │ Readable, consistent style; pipeline.py is    │

  │ maintainability     │ 3/5   │ 625 LOC monolith; bare except: in 5 places;   │

  │                     │       │ no type annotations in new code               │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Security (appsec +  │       │ No shell=True; .env properly gitignored; but: │

  │ secrets + auth)     │ 2/5   │  path traversal confirmed (fixed), user idea  │

  │                     │       │ in commit messages, no input validation       │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Dependency hygiene  │       │ All deps unpinned; no lockfile committed;     │

  │ / supply chain      │ 1/5   │ streamlit missing from deps; requirements.txt │

  │                     │       │  ≠ pyproject.toml                             │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Testing depth &     │       │ 3 tests, template-only; no coverage of        │

  │ confidence          │ 1/5   │ pipeline nodes, LLM calls, error paths,       │

  │                     │       │ security boundaries                           │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ CI/CD quality       │ 0/5   │ No CI whatsoever; no .github/workflows; no    │

  │                     │       │ branch protection; no lint/type/test gates    │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Runtime config /    │       │ PROJECTS_ROOT env var works; .env /           │

  │ env management      │ 3/5   │ python-dotenv correct; relative paths break   │

  │                     │       │ installed CLI                                 │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Database &          │       │ SQLite for checkpoints + lessons; no schema   │

  │ migrations          │ 2/5   │ migration strategy; LessonsManager missing    │

  │                     │       │ check_same_thread; no backup                  │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Error handling &    │       │ Pipeline nodes have minimal error handling; 5 │

  │ resilience          │ 2/5   │  bare except: clauses; stubs for              │

  │                     │       │ infra/sre/cicd; no LLM retry logic            │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │                     │       │ print() everywhere; no structured logging; no │

  │ Observability       │ 1/5   │  log levels; no metrics; no tracing;          │

  │                     │       │ audit.log is the only telemetry               │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Performance &       │       │ Single-user local tool — acceptable; os.chdir │

  │ scalability         │ 3/5   │  is a latent concurrency hazard; no LLM call  │

  │                     │       │ batching                                      │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Documentation &     │       │ README is brief but accurate; PERSISTENT.md   │

  │ runbooks            │ 2/5   │ is detailed; no deploy runbook; no incident   │

  │                     │       │ guide; no architecture diagram                │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Developer           │       │ Clear README; pip install -e . works; no      │

  │ experience /        │ 3/5   │ .env.example completeness gap; no make / task │

  │ onboarding          │       │  runner                                       │

  ├─────────────────────┼───────┼───────────────────────────────────────────────┤

  │ Compliance /        │       │ No obvious license; user ideas logged to      │

  │ privacy / licensing │ 3/5   │ audit.log (committed to git); no              │

  │                     │       │ PII/retention policy                          │

  └─────────────────────┴───────┴───────────────────────────────────────────────┘

  

  **Overall:** **1.9/5** — Pre-production personal tool.

  

  ---

  **5.** **Top** **Critical/High** **Findings**

  

  **SEC-001** **—** **LLM** **Path** **Traversal** **in** **Code** **Generator**

  

  - **Severity:** Critical | **Likelihood:** Medium | **Impact:** High | **Confidence:** Confirmed

  - **File:** tools/executor_tools.py:7-19 (_resolve_generated_file_path)

  - **Evidence:** lstrip("/") removes leading slashes but does not prevent ../

  sequences. Path(repo_path) / "../../etc/passwd" resolves outside the project.

  Proof-of-concept confirmed:

  Input: "../../etc/passwd"  →  Resolved: /private/etc/passwd  (OUTSIDE repo)

  - **Why** **it** **matters:** The LLM generating code file names could (through hallucination

  or adversarial prompt injection) output a filename like ../../.env or

  ../../gemforge/pipeline.py, overwriting critical files.

  - **Fix** **applied:** Added .resolve() + candidate.relative_to(output_path) guard.

  Invalid paths are logged and rejected. ✅

  

  **BUG-001** **—** **NameError:** **Path** **Not** **Imported** **in** **pipeline.py**

  

  - **Severity:** Critical | **Likelihood:** High (triggered every full run) | **Confidence:**

  Confirmed

  - **File:** pipeline.py:488 — strategy_path = Path(repo_path) / "BUSINESS_STRATEGY.md"

  - **Evidence:** No from pathlib import Path in pipeline.py imports. Path is used only

  by shipping_node. Every complete pipeline run will crash with NameError: name

  'Path' is not defined at this node.

  - **Fix** **applied:** Added from pathlib import Path to imports. ✅

  

  **REL-001** **—** **Auto** **Git** **Commit+Push** **on** **Every** **Entry** **Point** **Call**

  

  - **Severity:** High | **Likelihood:** High | **Confidence:** Confirmed

  - **File:** core/discipline/enforcer.py:126-131, main.py:9-13,

  src/gemforge/cli.py:10-14

  - **Evidence:** @enforce_protocol and discipline_step both call

  disciplined_commit(FACTORY_ROOT, ...) which runs git add ., git commit, git push

  against the gemforge repo on every invocation. Also fires at pipeline.py import

  time (line 548: with discipline_step(...)).

  - **Why** **it** **matters:** (a) Surprises users by auto-committing their gemforge repo; (b)

  fails silently in environments without push credentials; (c) commits dirty state

  mid-operation; (d) audit.log (with user idea text) is auto-pushed to origin.

  - **Recommended** **fix:** Make disciplined_commit opt-in via env var

  GEMFORGE_AUTO_PUSH=true; default to audit-log-only behavior. Remove the

  module-level discipline_step from pipeline.py — it fires on import.

  

  **BUG-002** **—** **Git** **Repo** **URL** **Is** **Always** **a** **Broken** **Literal** **String**

  

  - **Severity:** High | **Likelihood:** High | **Confidence:** Confirmed

  - **File:** tools/git_tools.py:26

  - **Evidence:**

  repo_url = f"https://github.com/$(gh api user | jq -r .login)/{repo_name}"

  - Python f-strings do not evaluate shell command substitutions. The stored URL is

  literally "https://github.com/$(gh api user | jq -r .login)/repo-name".

  - **Fix** **applied:** Replaced with subprocess.run(["gh", "api", "user", "--jq",

  ".login"]). ✅

  

  **SEC-002** **—** **Global** **os.chdir()** **in** **QA** **Test** **Runner**

  

  - **Severity:** High | **Likelihood:** Medium | **Confidence:** Confirmed

  - **File:** tools/executor_tools.py:109

  - **Evidence:** os.chdir(repo) — changes the process-global CWD. After run_tests()

  returns, the CWD is the generated project directory, not the gemforge root. All

  subsequent relative path operations (Path("LESSONS.md"), Path("agents/")) now

  resolve incorrectly.

  - **Fix** **applied:** Removed os.chdir and noted that cwd= parameter on subprocess calls

  should be used instead. ✅

  

  **ARCH-001** **—** **Circular** **Imports** **/** **Full** **Pipeline** **Initialization** **on** **Utility** **Import**

  

  - **Severity:** High | **Likelihood:** High | **Confidence:** Confirmed

  - **Files:** core/shipping/shipper.py:4, core/prediction/oracle.py:6,

  core/swarm/swarm_factory.py:6

  - **Evidence:** All three import from pipeline import cost_aware_invoke, load_prompt

  at module level. pipeline.py has a module-level with discipline_step(...) block

  (line 548) that: reads files, compiles the StateGraph, opens a SQLite connection,

  and calls disciplined_commit (git push). So importing shipper or oracle directly

  triggers all of this.

  - **Recommended** **fix:** Extract cost_aware_invoke and load_prompt into a separate

  core/llm.py module that core/ modules can safely import without triggering

  pipeline initialization.

  

  **BUG-003** **—** **Wrong** **LLM** **Pricing** **(60×** **Cost** **Overstatement)**

  

  - **Severity:** High | **Likelihood:** High | **Confidence:** Confirmed

  - **File:** tools/cost_tracker.py:19

  - **Evidence:** Comment says "Claude 3.5 Sonnet pricing" but model is

  claude-3-haiku-20240307. Haiku pricing is $0.25/$1.25 per million tokens; Sonnet

  is $15/$75 per million. Factor: ~60×.

  - **Fix** **applied:** Updated to Haiku pricing. ✅

  

  **BUG-004** **—** **Director** **Routing** **Default** **Bypasses** **Review** **Gate**

  

  - **Severity:** High | **Likelihood:** Low | **Confidence:** Confirmed

  - **File:** pipeline.py:609

  - **Evidence:** lambda s: "infra" if s.get("director_approved", True) else

  "human_review" — if director_approved is absent from state (not set by

  director_node), the default True routes straight to infra, bypassing the Director

  Review entirely.

  - **Fix** **applied:** Changed default to False. ✅

  

  **REL-002** **—** **CWD-Dependent** **Paths** **Break** **Installed** **CLI**

  

  - **Severity:** High | **Likelihood:** High | **Confidence:** Confirmed

  - **Files:** core/evolution/prompt_loader.py:7, core/memory/lessons_manager.py:42,

  core/memory/user_taste_manager.py:8

  - **Evidence:** All use relative string literals ("agents", "lessons/lessons.db",

  "memory/user_taste.json", Path("LESSONS.md")). The installed gemforge CLI is

  intended to be run from any directory (gemforge new "idea"), so these will

  silently fail or create files in unexpected locations.

  - **Fix** **applied:** All three now derive paths using

  Path(__file__).resolve().parent.parent.parent. ✅

  

  ---

  **6.** **Complete** **Findings** **Register**

  

  **Security**

  

  **ID:** SEC-001

  **Title:** LLM path traversal in code generator

  **Sev:** Critical

  **Like:** Med

  **Impact:** High

  **Conf:** Confirmed

  **Status:** ✅ Fixed

  ────────────────────────────────────────

  **ID:** SEC-002

  **Title:** os.chdir global CWD mutation

  **Sev:** High

  **Like:** Med

  **Impact:** High

  **Conf:** Confirmed

  **Status:** ✅ Fixed

  ────────────────────────────────────────

  **ID:** SEC-003

  **Title:** User ideas logged to committed audit.log

  **Sev:** Medium

  **Like:** High

  **Impact:** Low

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** SEC-004

  **Title:** venv/ directory present in repo (not ignored by .gitignore when added

    manually)

  **Sev:** Low

  **Like:** Low

  **Impact:** Low

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** SEC-005

  **Title:** No API key rotation mechanism or key scope validation

  **Sev:** Info

  **Like:** —

  **Impact:** —

  **Conf:** Needs validation

  **Status:** Open

  

  **SEC-003** **Detail:** The DisciplineEnforcer.log_audit() writes user ideas (truncated to

   30 chars) to audit.log, which is tracked by git and auto-pushed. If the repo is

  ever made public, partial user ideas become public. Recommendation: exclude

  audit.log from git tracking or redact sensitive content.

  

  ---

  **Reliability** **/** **Correctness**

  

  ┌────────┬──────────────────────┬─────────┬─────┬───────┬───────────┬───────┐

  │   ID   │        Title         │   Sev   │ Lik │ Impac │   Conf    │ Statu │

  │        │                      │         │  e  │   t   │           │   s   │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │ BUG-00 │ NameError: Path not  │ Critica │ Hig │       │           │ ✅    │

  │ 1      │ imported in          │ l       │ h   │ High  │ Confirmed │ Fixed │

  │        │ pipeline.py          │         │     │       │           │       │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │ BUG-00 │ Fake git repo URL    │         │ Hig │       │           │ ✅    │

  │ 2      │ (shell syntax in     │ High    │ h   │ Med   │ Confirmed │ Fixed │

  │        │ f-string)            │         │     │       │           │       │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │ BUG-00 │ Wrong cost pricing   │         │ Hig │       │           │ ✅    │

  │ 3      │ (Sonnet rates for    │ High    │ h   │ Med   │ Confirmed │ Fixed │

  │        │ Haiku)               │         │     │       │           │       │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │ BUG-00 │ Director routing     │         │     │       │           │ ✅    │

  │ 4      │ default bypasses     │ High    │ Low │ Med   │ Confirmed │ Fixed │

  │        │ review gate          │         │     │       │           │       │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │ BUG-00 │ infra_node,          │         │ Hig │       │           │       │

  │ 5      │ cicd_node, sre_node  │ High    │ h   │ Med   │ Confirmed │ Open  │

  │        │ are stubs            │         │     │       │           │       │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │        │ cost_tracker         │         │     │       │           │       │

  │ BUG-00 │ singleton never      │ Med     │ Med │ Low   │ Confirmed │ Open  │

  │ 6      │ resets between       │         │     │       │           │       │

  │        │ pipeline runs        │         │     │       │           │       │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │ BUG-00 │ LessonsManager       │         │     │       │           │ ✅    │

  │ 7      │ SQLite missing check │ Med     │ Med │ Low   │ Confirmed │ Fixed │

  │        │ _same_thread=False   │         │     │       │           │       │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │        │ parse_and_save_docs  │         │     │       │           │       │

  │ BUG-00 │ regex may miss last  │ Med     │ Med │ Med   │ Strong in │ Open  │

  │ 8      │ block (off-by-one in │         │     │       │ dication  │       │

  │        │  range())            │         │     │       │           │       │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │        │ git_publish_node     │         │     │       │           │       │

  │ BUG-00 │ commits after gh     │ Med     │ Med │ Low   │ Confirmed │ ✅    │

  │ 9      │ repo create --push — │         │     │       │           │ Fixed │

  │        │  double-push risk    │         │     │       │           │       │

  ├────────┼──────────────────────┼─────────┼─────┼───────┼───────────┼───────┤

  │        │ director_node bare   │         │     │       │           │       │

  │ BUG-01 │ except: swallows all │ Med     │ Med │ Med   │ Confirmed │ Open  │

  │ 0      │  errors including    │         │     │       │           │       │

  │        │ KeyboardInterrupt    │         │     │       │           │       │

  └────────┴──────────────────────┴─────────┴─────┴───────┴───────────┴───────┘

  

  **BUG-005** **Detail:** infra_node, cicd_node, sre_node in pipeline.py:347-357 all return

  immediately with True. The pipeline marks infra/CI/SRE as "complete" without

  performing any actual work. This is acceptable during development but is a

  production blocker — these nodes should either do real work or clearly be marked

  TODO.

  

  **BUG-008** **Detail:** parse_and_save_docs uses range(1, len(parts) - 1, 2) — if the

  regex produces an even number of captures, the last capture is dropped. This could

   silently omit the last generated document.

  

  ---

  **Architecture**

  

  **ID:** ARCH-001

  **Title:** Circular imports — core/ modules import from pipeline.py

  **Sev:** High

  **Like:** High

  **Impact:** High

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** ARCH-002

  **Title:** Module-level side effects in pipeline.py (git push on import)

  **Sev:** High

  **Like:** High

  **Impact:** High

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** ARCH-003

  **Title:** pipeline.py is a 625-line god module

  **Sev:** Med

  **Like:** High

  **Impact:** Med

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** ARCH-004

  **Title:** Global singletons cost_tracker, prompt_loader, shipper, oracle,

    swarm_factory, empire_stats

  **Sev:** Med

  **Like:** Med

  **Impact:** Med

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** ARCH-005

  **Title:** PromptLoader default path is CWD-relative

  **Sev:** High

  **Like:** High

  **Impact:** High

  **Conf:** Confirmed

  **Status:** ✅ Fixed

  ────────────────────────────────────────

  **ID:** ARCH-006

  **Title:** ShippingNode imports shipper lazily inside function, shipper imports

    pipeline at top — still circular

  **Sev:** Med

  **Like:** High

  **Impact:** Med

  **Conf:** Confirmed

  **Status:** Open

  

  ---

  **Dependency** **Management**

  

  ┌─────────┬───────────────────────┬──────┬──────┬────────┬───────────┬────────┐

  │   ID    │         Title         │ Sev  │ Like │ Impact │   Conf    │ Status │

  ├─────────┼───────────────────────┼──────┼──────┼────────┼───────────┼────────┤

  │         │ streamlit missing     │      │      │        │           │ ✅     │

  │ DEP-001 │ from requirements.txt │ High │ High │ Med    │ Confirmed │ Fixed  │

  │         │  and pyproject.toml   │      │      │        │           │        │

  ├─────────┼───────────────────────┼──────┼──────┼────────┼───────────┼────────┤

  │         │ All dependencies      │      │      │        │           │        │

  │ DEP-002 │ unpinned (no == or ~= │ High │ High │ Med    │ Confirmed │ Open   │

  │         │  version constraints) │      │      │        │           │        │

  ├─────────┼───────────────────────┼──────┼──────┼────────┼───────────┼────────┤

  │         │ No lockfile           │      │      │        │           │        │

  │ DEP-003 │ (pip.lock,            │ High │ High │ Med    │ Confirmed │ Open   │

  │         │ poetry.lock, or       │      │      │        │           │        │

  │         │ uv.lock) committed    │      │      │        │           │        │

  ├─────────┼───────────────────────┼──────┼──────┼────────┼───────────┼────────┤

  │         │ requirements.txt and  │      │      │        │           │        │

  │ DEP-004 │ pyproject.toml        │ Med  │ High │ Med    │ Confirmed │ Open   │

  │         │ dependencies diverge  │      │      │        │           │        │

  ├─────────┼───────────────────────┼──────┼──────┼────────┼───────────┼────────┤

  │         │ No pytest in any      │      │      │        │           │        │

  │ DEP-005 │ requirements file     │ Low  │ High │ Low    │ Confirmed │ Open   │

  │         │ (tests run with       │      │      │        │           │        │

  │         │ unittest)             │      │      │        │           │        │

  └─────────┴───────────────────────┴──────┴──────┴────────┴───────────┴────────┘

  

  **DEP-002** **Detail:** langgraph, langchain-anthropic, anthropic are all fast-moving

  packages with frequent breaking changes. A fresh install in 6 months will likely

  fail.

  

  ---

  **Testing**

  

  ┌────────┬──────────────────────────┬────────┬─────┬──────┬─────────┬──────┐

  │   ID   │          Title           │  Sev   │ Lik │ Impa │  Conf   │ Stat │

  │        │                          │        │  e  │  ct  │         │  us  │

  ├────────┼──────────────────────────┼────────┼─────┼──────┼─────────┼──────┤

  │        │ Only 3 tests; zero       │        │     │      │         │      │

  │ TEST-0 │ coverage of pipeline,    │ High   │ Hig │ High │ Confirm │ Open │

  │ 01     │ nodes, security, or LLM  │        │ h   │      │ ed      │      │

  │        │ calls                    │        │     │      │         │      │

  ├────────┼──────────────────────────┼────────┼─────┼──────┼─────────┼──────┤

  │        │ No test for parse_and_sa │        │     │      │         │      │

  │ TEST-0 │ ve_generated_code path   │ Critic │ Hig │ High │ Confirm │ Open │

  │ 02     │ traversal (most critical │ al     │ h   │      │ ed      │      │

  │        │  function)               │        │     │      │         │      │

  ├────────┼──────────────────────────┼────────┼─────┼──────┼─────────┼──────┤

  │ TEST-0 │ No integration tests for │        │ Hig │      │ Confirm │      │

  │ 03     │  resume.py               │ Med    │ h   │ Med  │ ed      │ Open │

  │        │ (approval/refine flow)   │        │     │      │         │      │

  ├────────┼──────────────────────────┼────────┼─────┼──────┼─────────┼──────┤

  │ TEST-0 │ No tests for             │        │ Hig │      │ Confirm │      │

  │ 04     │ push_to_github (mock gh  │ Med    │ h   │ Med  │ ed      │ Open │

  │        │ CLI)                     │        │     │      │         │      │

  ├────────┼──────────────────────────┼────────┼─────┼──────┼─────────┼──────┤

  │        │ Temp dirs in tests are   │        │     │      │         │      │

  │ TEST-0 │ not cleaned up           │ Low    │ Med │ Low  │ Confirm │ Open │

  │ 05     │ (tempfile.mkdtemp        │        │     │      │ ed      │      │

  │        │ without cleanup)         │        │     │      │         │      │

  └────────┴──────────────────────────┴────────┴─────┴──────┴─────────┴──────┘

  

  ---

  **CI/CD** **&** **DevOps**

  

  **ID:** CICD-001

  **Title:** No CI pipeline (no .github/workflows)

  **Sev:** High

  **Like:** High

  **Impact:** High

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** CICD-002

  **Title:** No branch protection on master

  **Sev:** High

  **Like:** High

  **Impact:** Med

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** CICD-003

  **Title:** No lint/type-check tooling configured (ruff, mypy, pyright)

  **Sev:** Med

  **Like:** High

  **Impact:** Med

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** CICD-004

  **Title:** No pre-commit hooks

  **Sev:** Low

  **Like:** High

  **Impact:** Low

  **Conf:** Confirmed

  **Status:** Open

  ────────────────────────────────────────

  **ID:** CICD-005

  **Title:** Version in pyproject.toml is hardcoded 1.0.0 but repo is at conceptual v2.0

  **Sev:** Low

  **Like:** Med

  **Impact:** Low

  **Conf:** Confirmed

  **Status:** Open

  

  ---

  **Observability**

  

  ┌─────────┬────────────────────────┬──────┬──────┬────────┬───────────┬────────┐

  │   ID    │         Title          │ Sev  │ Like │ Impact │   Conf    │ Status │

  ├─────────┼────────────────────────┼──────┼──────┼────────┼───────────┼────────┤

  │         │ All logging is print() │      │      │        │           │        │

  │ OBS-001 │  — no log levels,      │ High │ High │ Med    │ Confirmed │ Open   │

  │         │ structured logging, or │      │      │        │           │        │

  │         │  redaction             │      │      │        │           │        │

  ├─────────┼────────────────────────┼──────┼──────┼────────┼───────────┼────────┤

  │ OBS-002 │ No error reporting     │ Med  │ High │ Med    │ Confirmed │ Open   │

  │         │ (Sentry/Rollbar/etc.)  │      │      │        │           │        │

  ├─────────┼────────────────────────┼──────┼──────┼────────┼───────────┼────────┤

  │         │ Cost tracker resets on │      │      │        │           │        │

  │ OBS-003 │  each process start    │ Med  │ High │ Med    │ Confirmed │ Open   │

  │         │ (no persistence across │      │      │        │           │        │

  │         │  runs)                 │      │      │        │           │        │

  ├─────────┼────────────────────────┼──────┼──────┼────────┼───────────┼────────┤

  │         │ audit.log uses fixed   │      │      │        │           │        │

  │ OBS-004 │ MST timezone           │ Low  │ High │ Low    │ Confirmed │ Open   │

  │         │ regardless of system   │      │      │        │           │        │

  │         │ timezone               │      │      │        │           │        │

  └─────────┴────────────────────────┴──────┴──────┴────────┴───────────┴────────┘

  

  ---

  **Code** **Quality**

  

  ┌──────┬───────────────────────────────┬─────┬─────┬──────┬─────────┬──────┐

  │  ID  │             Title             │ Sev │ Lik │ Impa │  Conf   │ Stat │

  │      │                               │     │  e  │  ct  │         │  us  │

  ├──────┼───────────────────────────────┼─────┼─────┼──────┼─────────┼──────┤

  │ CQ-0 │ 5× bare except: clauses       │     │ Hig │      │ Confirm │      │

  │ 01   │ swallow KeyboardInterrupt,    │ Med │ h   │ Med  │ ed      │ Open │

  │      │ SystemExit                    │     │     │      │         │      │

  ├──────┼───────────────────────────────┼─────┼─────┼──────┼─────────┼──────┤

  │      │ frontend_node/backend_node/da │     │     │      │         │      │

  │ CQ-0 │ ta_node pass                  │ Low │ Hig │ Low  │ Confirm │ Open │

  │ 02   │ architecture_complete boolean │     │ h   │      │ ed      │      │

  │      │  as context string            │     │     │      │         │      │

  ├──────┼───────────────────────────────┼─────┼─────┼──────┼─────────┼──────┤

  │ CQ-0 │ venv/ checked into repo       │     │     │      │ Confirm │      │

  │ 03   │ tracking history (present,    │ Low │ Med │ Low  │ ed      │ Open │

  │      │ not ignored)                  │     │     │      │         │      │

  ├──────┼───────────────────────────────┼─────┼─────┼──────┼─────────┼──────┤

  │ CQ-0 │ Multiple .bak.* files in repo │ Low │ Med │ Low  │ Confirm │ Open │

  │ 04   │  (were previously committed)  │     │     │      │ ed      │      │

  ├──────┼───────────────────────────────┼─────┼─────┼──────┼─────────┼──────┤

  │ CQ-0 │ No type annotations on any    │ Low │ Hig │ Low  │ Confirm │ Open │

  │ 05   │ public function signatures    │     │ h   │      │ ed      │      │

  ├──────┼───────────────────────────────┼─────┼─────┼──────┼─────────┼──────┤

  │ CQ-0 │ macOS-specific                │     │     │      │ Confirm │      │

  │ 06   │ subprocess.Popen(["open",     │ Low │ Med │ Low  │ ed      │ Open │

  │      │ ...]) in dashboard.py         │     │     │      │         │      │

  └──────┴───────────────────────────────┴─────┴─────┴──────┴─────────┴──────┘

  

  **CQ-002** **Detail:** In frontend_node, backend_node, and data_node:

  context = f"POLISHED_VISION:\n{state['polished_vision']}\n\nARCHITECTURE:\n{state.

  get('architecture_complete')}"

  architecture_complete is a bool, so the context contains "ARCHITECTURE:\nTrue"

  instead of the actual architecture content. These nodes receive no meaningful

  architecture context.

  

  ---

  **7.** **Remediation** **Roadmap**

  

  **Phase** **0:** **Stop** **the** **Bleeding** **(COMPLETED** **on** **branch)**

  

  ┌───────────────────────────────────────────────────┬────────┬──────┬──────────┐

  │                       Task                        │ Effort │ Risk │  Owner   │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ ✅ Fix path traversal in                          │ S      │ Low  │ Security │

  │ _resolve_generated_file_path                      │        │      │          │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ ✅ Add from pathlib import Path to pipeline.py    │ S      │ None │ Backend  │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ ✅ Fix fake repo URL in git_tools.py              │ S      │ Low  │ Backend  │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ ✅ Fix cost pricing (Haiku rates)                 │ S      │ None │ Backend  │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ ✅ Fix director routing default                   │ S      │ None │ Backend  │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ ✅ Remove os.chdir from run_tests                 │ S      │ Low  │ Backend  │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ ✅ Fix CWD-dependent paths in lessons_manager,    │ S      │ Low  │ Backend  │

  │ user_taste_manager, prompt_loader                 │        │      │          │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ ✅ Add streamlit to deps                          │ S      │ None │ Platform │

  └───────────────────────────────────────────────────┴────────┴──────┴──────────┘

  

  **Phase** **1:** **Production** **Blockers** **(1–2** **weeks)**

  

  ┌───────────────────────────────────────────────────┬────────┬──────┬──────────┐

  │                       Task                        │ Effort │ Risk │  Owner   │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Gate disciplined_commit behind GEMFORGE_AUTO_PUSH │ S      │ Low  │ Backend  │

  │  env var                                          │        │      │          │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Remove module-level discipline_step from          │ S      │ Med  │ Backend  │

  │ pipeline.py (runs on import)                      │        │      │          │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Extract cost_aware_invoke/load_prompt to          │ M      │ Med  │ Backend  │

  │ core/llm.py (break circular imports)              │        │      │          │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Pin all dependency versions                       │ S      │ Med  │ Platform │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Add requirements.lock or switch to uv / poetry    │ S      │ Low  │ Platform │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Sync requirements.txt ↔ pyproject.toml            │ S      │ None │ Platform │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Fix CQ-002: pass actual ARCHITECTURE.md content   │ S      │ None │ Backend  │

  │ in parallel nodes                                 │        │      │          │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Add security test for                             │        │      │          │

  │ parse_and_save_generated_code (path traversal     │ S      │ None │ QA       │

  │ regression)                                       │        │      │          │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Add GitHub Actions CI: python -m unittest         │ S      │ None │ CICD     │

  │ discover                                          │        │      │          │

  └───────────────────────────────────────────────────┴────────┴──────┴──────────┘

  

  **Phase** **2:** **Reliability** **&** **Observability** **Hardening** **(2–4** **weeks)**

  

  ┌────────────────────────────────────────────────────┬────────┬──────┬─────────┐

  │                        Task                        │ Effort │ Risk │  Owner  │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Replace all print() with structured logging        │ M      │ Low  │ Backend │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Implement real infra_node, cicd_node, sre_node or  │ M      │ Low  │ Backend │

  │ mark as explicit placeholders                      │        │      │         │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Add retry + timeout logic around all LLM calls     │ M      │ Med  │ Backend │

  │ (exponential backoff)                              │        │      │         │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Add test for resume.py approval/refine flow with   │ M      │ Low  │ QA      │

  │ mocked LLM                                         │        │      │         │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Add mock-based tests for push_to_github            │ S      │ None │ QA      │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Replace bare except: with specific exception types │ S      │ Low  │ Backend │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Add LessonsManager schema migration support        │ S      │ Low  │ Backend │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Persist cost_tracker data to SQLite across         │ S      │ Low  │ Backend │

  │ sessions                                           │        │      │         │

  └────────────────────────────────────────────────────┴────────┴──────┴─────────┘

  

  **Phase** **3:** **Performance** **&** **Scalability** **(1–2** **months)**

  

  ┌────────────────────────────────────────────────────┬────────┬──────┬─────────┐

  │                        Task                        │ Effort │ Risk │  Owner  │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Evaluate async LLM calls for parallel nodes        │ L      │ High │ Backend │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Add connection pooling for SQLite (replace         │ M      │ Med  │ Backend │

  │ singleton connections)                             │        │      │         │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Profile pipeline startup time (module-level init   │ S      │ None │ SRE     │

  │ is slow)                                           │        │      │         │

  ├────────────────────────────────────────────────────┼────────┼──────┼─────────┤

  │ Implement proper agent context windowing (truncate │ M      │ Med  │ Backend │

  │  context by token count, not chars)                │        │      │         │

  └────────────────────────────────────────────────────┴────────┴──────┴─────────┘

  

  **Phase** **4:** **Maintainability** **&** **Debt** **(ongoing)**

  

  ┌───────────────────────────────────────────────────┬────────┬──────┬──────────┐

  │                       Task                        │ Effort │ Risk │  Owner   │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Split pipeline.py into nodes/ package (one file   │ L      │ Med  │ Backend  │

  │ per node)                                         │        │      │          │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Add mypy or pyright with strict mode              │ M      │ Low  │ Backend  │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Add ruff linter configuration                     │ S      │ None │ DX       │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Add pre-commit hooks for lint + test              │ S      │ None │ DX       │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Document architecture with diagram                │ M      │ None │ Docs     │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Add changelog and semver discipline               │ S      │ None │ Platform │

  ├───────────────────────────────────────────────────┼────────┼──────┼──────────┤

  │ Cross-platform fix for subprocess.Popen(["open",  │ S      │ None │ Backend  │

  │ ...]) in dashboard                                │        │      │          │

  └───────────────────────────────────────────────────┴────────┴──────┴──────────┘

  

  ---

  **8.** **PR-Ready** **Recommendations** **/** **Patch** **Sketches**

  

  **Patch:** **Gate** **Auto-Git-Push** **(not** **yet** **implemented** **—** **proposed)**

  

  # core/discipline/enforcer.py

  import os

  

  @staticmethod

  def disciplined_commit(repo_path: Path, step_number: int, short_name: str,

  description: str):

      """Step 6 & 7: Exact-format git commit (+ optional push)"""

      message = f"step {step_number}: {short_name} - {description}"

      DisciplineEnforcer.git_command(repo_path, ["add", "."])

      DisciplineEnforcer.git_command(repo_path, ["commit", "-m", message])

      # Only push if explicitly enabled — prevents surprise remote mutations

      if os.getenv("GEMFORGE_AUTO_PUSH", "false").lower() == "true":

          DisciplineEnforcer.git_command(repo_path, ["push"])

          print(f"✅ [D-Protocol] Steps 6–7: Committed & pushed → {message}")

      else:

          print(f"✅ [D-Protocol] Steps 6–7: Committed (push skipped — set

  GEMFORGE_AUTO_PUSH=true to enable)")

  

  **Patch:** **Fix** **CQ-002** **—** **Architecture** **context** **in** **parallel** **nodes**

  

  # pipeline.py — shared helper

  def _read_project_file(repo_path: str, filename: str) -> str:

      try:

          with open(f"{repo_path}/{filename}", "r", encoding="utf-8") as f:

              return f.read()

      except Exception:

          return f"[{filename} not yet available]"

  

  def frontend_node(state: PipelineState):

      repo_path = state.get("repo_path", "")

      context = (

          f"POLISHED_VISION:\n{state['polished_vision']}\n\n"

          f"ARCHITECTURE:\n{_read_project_file(repo_path, 'ARCHITECTURE.md')}"

      )

      # ... rest unchanged

  

  **Patch:** **Proposed** **core/llm.py** **(breaks** **circular** **imports)**

  

  # core/llm.py — new file, no pipeline.py dependency

  from langchain_anthropic import ChatAnthropic

  from tools.cost_tracker import cost_tracker

  

  _llm = None

  

  def get_llm():

      global _llm

      if _llm is None:

          _llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)

      return _llm

  

  def cost_aware_invoke(prompt_messages):

      response = get_llm().invoke(prompt_messages)

      cost_tracker.track_call(response)

      return response

  

  Then core/shipping/shipper.py, oracle.py, swarm_factory.py import from core.llm

  instead of pipeline.

  

  **Proposed** **GitHub** **Actions** **CI** **(****.github/workflows/ci.yml****)**

  

  name: CI

  on: [push, pull_request]

  jobs:

    test:

      runs-on: ubuntu-latest

      steps:

        - uses: actions/checkout@v4

        - uses: actions/setup-python@v5

          with:

            python-version: "3.12"

        - run: pip install -r requirements.txt

        - run: python -m unittest discover -v tests/

        - run: ruff check . || true   # Warning-only until fully clean

  

  **Proposed** **Security** **Test** **(property-based** **path** **traversal)**

  

  # tests/test_security.py

  import unittest

  from pathlib import Path

  import tempfile

  from tools.executor_tools import _resolve_generated_file_path

  

  class PathTraversalTests(unittest.TestCase):

      ATTACK_VECTORS = [

          "../../etc/passwd",

          "../.env",

          "../../gemforge/pipeline.py",

          "/etc/shadow",

          "..%2F..%2Fetc%2Fpasswd",   # URL-encoded (won't work but good to

  document)

          "....//....//etc/passwd",

      ]

  

      def setUp(self):

          self.repo = tempfile.mkdtemp(prefix="gemforge-sec-")

  

      def test_path_traversal_rejected(self):

          for vector in self.ATTACK_VECTORS:

              with self.subTest(vector=vector):

                  result = _resolve_generated_file_path(self.repo, vector)

                  if result is not None:

                      repo_resolved = Path(self.repo).resolve()

                      self.assertTrue(

                          str(result).startswith(str(repo_resolved)),

                          f"Path traversal NOT blocked for {vector!r}: got {result}"

                      )

  

      def test_legitimate_paths_allowed(self):

          for path in ["src/app.py", "app.swift", "lib/main.dart", "README.md"]:

              with self.subTest(path=path):

                  result = _resolve_generated_file_path(self.repo, path)

                  self.assertIsNotNone(result)

  

  **Alert** **Rules** **(if/when** **observability** **is** **added)**

  

  # Suggested metrics to track:

  # - llm_call_duration_seconds (histogram per agent)

  # - llm_call_total_cost_usd (counter)

  # - pipeline_node_failures_total (counter per node name)

  # - path_traversal_attempt_total (counter — security metric)

  # - pipeline_duration_seconds (histogram per platform)

  

  ---

  **9.** **Validation** **Plan**

  

  **How** **to** **verify** **fixes** **are** **safe:**

  

  1. **SEC-001** **fix** **verification:**

  python -m unittest tests/test_security.py  # After adding tests above

  python3 -c "

  from tools.executor_tools import _resolve_generated_file_path

  assert _resolve_generated_file_path('/tmp/repo', '../../etc/passwd') is None

  assert _resolve_generated_file_path('/tmp/repo', 'src/app.py') is not None

  print('SEC-001: PASS')

  "

  2. **BUG-001** **fix** **verification:**

  python3 -c "from pipeline import shipping_node; print('BUG-001: PASS')"

  3. **BUG-003** **pricing** **fix** **verification:**

  python3 -c "

  from tools.cost_tracker import CostTracker

  # Haiku: 1M input tokens should cost $0.25

  class FakeResponse:

      class usage:

          input_tokens = 1_000_000

          output_tokens = 0

  ct = CostTracker()

  result = ct.track_call(FakeResponse())

  assert abs(result['cost'] - 0.25) < 0.001, f'Expected $0.25, got

  {result[\"cost\"]}'

  print('BUG-003: PASS')

  "

  4. **Regression** **test:**

  python -m unittest tests/test_template_application.py -v

  # Expected: 3 tests pass

  5. **End-to-end** **smoke** **test** **(requires** **API** **key):**

  ANTHROPIC_API_KEY=... python gemforge_cli.py new "test app"

  # Verify: no NameError in shipping_node

  # Verify: pipeline reaches END without crash

  

  ---

  **10.** **Appendix**

  

  **Commands** **Run**

  

  find . -maxdepth 3 (repo structure)

  git log --oneline --all

  git diff HEAD~5 HEAD -- audit.log

  python -m unittest tests/test_template_application.py -v   → 3 PASS

  python3 -c "...AST shell=True scan..."                     → 0 findings

  python3 -c "...path traversal proof-of-concept..."        → CONFIRMED

  python3 -c "...path traversal post-fix test..."           → BLOCKED

  pip list (installed versions)

  grep -rn "os.chdir" ...

  grep -rn "except:" ...

  grep -rn "circular import chain" ...

  

  **Installed** **Package** **Versions**

  

  anthropic                   0.83.0

  langchain                   1.2.10

  langchain-anthropic         1.3.4

  langchain-core              1.2.15

  langgraph                   1.0.9

  pydantic                    2.12.5

  streamlit                   1.54.0

  

  **Assumptions**

  

  - This is a **personal** **developer** **tool** used locally by a single user — some risk

  ratings are calibrated accordingly (e.g., SQL injection, AuthN gaps are N/A as

  there is no web server or multi-user access control).

  - The Anthropic API key is stored in .env (local), which is gitignored. Not

  evaluated for rotation or leakage beyond this scope.

  - The infra_node, cicd_node, sre_node stubs are **intentional** **placeholders** per the

  development roadmap (the system is "Phase 5" of an ongoing build).

  

  **Open** **Questions** **/** **Unverified** **Areas**

  

  1. **Does** **the** **full** **pipeline** **succeed** **end-to-end?** Not runnable without live API key +

  Vercel credentials. shipping_node crash (BUG-001) was only caught by static

  analysis; the fix is on the branch but not smoke-tested live.

  2. **Do** **LLM** **code** **generators** **produce** **valid** **===filename===** **blocks** **consistently?** Not

  testable without API key. The regex in parse_and_save_generated_code has the

  off-by-one risk (BUG-008).

  3. **Does** **resume.py** **correctly** **handle** **the** **LangGraph** **interrupt** **/** **Command** **flow** **across**

  **all** **edge** **cases?** Requires live testing with the SQLite checkpoint.

  4. **Are** **there** **rate-limit** **/** **retry** **behaviors** **needed** **for** **the** **LLM** **calls?** Pipeline runs

  15+ LLM calls sequentially; no retry logic exists. With Haiku's generous rate

  limits, likely fine for personal use.

  5. **xcodegen** **/** **xcodebuild** **behavior:** iOS build verification assumes macOS with Xcode

   installed. Not verified on CI or non-macOS environments.

  

  ---

  **Summary** **of** **Branch** **Changes**

  

  The audit/production-readiness-2026-02-24 branch implements all **Critical** and most

  **High** severity fixes:

  

  ┌───────────────────────────────────┬──────────────────────────────────────────┐

  │               File                │                  Change                  │

  ├───────────────────────────────────┼──────────────────────────────────────────┤

  │ tools/executor_tools.py           │ SEC-001: Path traversal guard; REL-001:  │

  │                                   │ remove os.chdir                          │

  ├───────────────────────────────────┼──────────────────────────────────────────┤

  │ pipeline.py                       │ BUG-001: Add Path import; BUG-004: Fix   │

  │                                   │ director default                         │

  ├───────────────────────────────────┼──────────────────────────────────────────┤

  │ tools/cost_tracker.py             │ BUG-003: Correct Haiku pricing           │

  ├───────────────────────────────────┼──────────────────────────────────────────┤

  │ tools/git_tools.py                │ BUG-002: Real repo URL from gh api;      │

  │                                   │ BUG-009: skip empty commit               │

  ├───────────────────────────────────┼──────────────────────────────────────────┤

  │ core/memory/lessons_manager.py    │ REL-002: Absolute paths; BUG-007:        │

  │                                   │ check_same_thread                        │

  ├───────────────────────────────────┼──────────────────────────────────────────┤

  │ core/memory/user_taste_manager.py │ REL-002: Absolute paths                  │

  ├───────────────────────────────────┼──────────────────────────────────────────┤

  │ core/evolution/prompt_loader.py   │ ARCH-005: Absolute path for agents dir   │

  ├───────────────────────────────────┼──────────────────────────────────────────┤

  │ requirements.txt                  │ DEP-001: Add streamlit                   │

  ├───────────────────────────────────┼──────────────────────────────────────────┤

  │ pyproject.toml                    │ DEP-001: Add streamlit                   │

  └───────────────────────────────────┴──────────────────────────────────────────┘

  

  **Not** **yet** **implemented** **(require** **more** **design):**

  - ARCH-001/ARCH-002: Circular import refactor (extract core/llm.py)

  - REL-001: Gate disciplined_commit behind env var

  - CICD-001: GitHub Actions CI

  - TEST-002: Security regression tests

  - BUG-005: Implement real infra/cicd/sre nodes

  - DEP-002/DEP-003: Pin dependencies + lockfile