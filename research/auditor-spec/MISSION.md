# Standalone GemForge Auditor

Goal: Extract the "Forensic Auditor" logic from GemForge into a tiny, zero-dependency Python package.

The user should be able to run `gf-audit .` and get a clean `AUDIT.md` without needing the full LangGraph pipeline or an Anthropic API key (it should support local LLMs or just perform structural analysis).
