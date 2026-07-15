# A.I.M. Modular Tool Registry

This document serves as the external registry for the mechanical tools available to the Operator and Agents via the `aim` (Antigravity) CLI.

## 1. GitOps & Lifecycle Tools
* **`aim bug <title>`**: Opens a GitHub issue to track a bug. Use `--context`, `--failure`, and `--intent` for headless agent submissions.
* **`aim fix <id>`**: Checks out a dedicated Git worktree branch (`fix/issue-<id>`) to surgically fix an issue without polluting the main directory.
* **`aim push <message>`**: Pushes your current isolated branch to the remote repository and generates a Pull Request.
* **`aim promote`**: Archives the current `main` branch, safely merges the active dev branch, and prunes the local workspace.
* **`aim prune-remote`**: Garbage collects stale `archive-fix/*` and `fix/issue-*` remote branches.

## 2. Memory & Intelligence (Hybrid RAG)
* **`aim search "<query>"`**: Executes a LanceDB Hybrid Search (BM25 + Semantic) against the Engram DB and local markdown wikis.
* **`aim map`**: Prints a lightweight "Knowledge Map" of all currently loaded documentation titles.
* **`aim audit`**: Synthesizes a strategic overarching summary from the noise-reduced session history databases.

## 3. Operations & Sandboxing
* **`aim doctor`**: Validates the host environment, checking for correct Python versions and LanceDB dependencies.
* **`aim reincarnate`**: Triggers the Reincarnation Protocol to handoff context securely to a new agent session.
* **`aim delegate`**: Spawns parallel sub-agents (the RLM pattern) to execute multi-file analysis simultaneously.
