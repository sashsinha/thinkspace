<p align="center">
<a href="https://github.com/sashsinha/thinkspace">
  <img alt="ThinkSpace Logo" src="https://raw.githubusercontent.com/sashsinha/thinkspace/main/logo.png">
</a>
</p>

<h1 align="center">ThinkSpace</h1>

<h3 align="center">Context-Aware Scratchpad</h3>

<br/>

<p align="center">
<a href="https://raw.githubusercontent.com/sashsinha/thinkspace/main/LICENSE">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green.svg">
</a>
<a href="https://pypi.org/project/thinkspace/">
  <img src="https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macos-lightgrey" alt="Supported Platforms">
</a>
<a href="https://pypi.org/project/thinkspace/">
  <img alt="PyPI Supported Versions" src="https://img.shields.io/pypi/pyversions/thinkspace.svg">
</a>
<a href="https://pypi.org/project/thinkspace/">
  <img alt="PyPI" src="https://img.shields.io/pypi/v/thinkspace">
</a>
<a href="https://pypi.org/project/thinkspace/">
  <img alt="PyPI Status" src="https://img.shields.io/pypi/status/thinkspace">
</a>
<a href="https://pepy.tech/project/thinkspace">
  <img alt="Downloads" src="https://pepy.tech/badge/thinkspace">
</a>
</p>

- **Why:** Context switching to Notion/Obsidian/Todoist kills focus.
- **What:** `thinkspace note "todo: fix env var issue"` — later: `thinkspace search "env"`

---

## ✨ Features

- 🏷️ **Auto-tags** every note with your **project** (Git repo or folder) and **time buckets** (YYYY, YYYY‑MM, YYYY‑MM‑DD).
- 🔎 **Search** by text, tags, project, or time window. Uses SQLite with FTS5 full-text indexes when available, otherwise runs compatible LIKE queries.
- 📦 Zero-config local store in your user data dir (e.g. `~/.local/share/thinkspace/notes.db`).
- 🎨 **Rich CLI output**: readable tables, panels, and helpful highlighting.
- 🗑️ **Safe deletes** with per-note confirmation so you can clean up old snippets.
- 🧰 Portable single dependency stack (Typer + Rich + Platformdirs).

---

## 🚀 Quickstart

```bash
pip install thinkspace-cli
# or from source
pip install .
```

Add a note:

```bash
thinkspace note "todo: fix env var issue"
```

Search later:

```bash
thinkspace search "env"
```

List recent notes:

```bash
thinkspace list --limit 10
```

Filter by project:

```bash
thinkspace search "todo" --project my-repo
```

Show top tags:

```bash
thinkspace tags
```

Export to Markdown:

```bash
thinkspace export --out notes.md
```

Delete a note:

```bash
thinkspace delete 42
```

---

## 🧩 Commands

- `note [TEXT]` – Capture a note. Use `--tag` multiple times to add manual tags.
- `search [QUERY]` – Full‑text search with optional filters: `--project`, `--since`, `--until`, `--limit`.
- `list` – Show most recent notes.
- `tags` – Show top tags (auto & manual).
- `db-path` – Print the notes DB path.
- `export` – Export all notes (optionally filtered) to Markdown.
- `delete [ID ...]` – Remove one or more notes (prompts for confirmation unless `--yes` is provided).

---

## 🏗️ How it works

- On first run, Thinkspace creates a tiny SQLite DB at your user data directory.
- Notes are stored with fields: `id`, `text`, `project`, `tags`, `created_at`, `path`.
- If SQLite **FTS5** (the built-in full-text search extension) is available, Thinkspace builds an FTS5 virtual table so queries tokenize text and return ranked matches instantly.
- On systems without FTS5 compiled in, Thinkspace falls back to standard SQL `LIKE` clauses—simple substring matching that works everywhere, though with slower lookups on large notebooks.

---

## 🧪 Testing

```bash
pip install -r requirements-dev.txt  # installs pytest & mypy
mypy src
pytest -q
```

## 🧹 Linting

```bash
pip install -r requirements-dev.txt  # installs ruff
ruff check .
ruff format .
```

---

## 📦 Publishing to PyPI

1. Update version in `pyproject.toml`.
2. Build:
   ```bash
   python -m build
   ```
3. Upload:
   ```bash
   python -m twine upload dist/*
   ```

---


## ⚡ uv workflow

Prefer using [uv](https://docs.astral.sh/uv/) for speed and reproducibility.

```bash
# 1) Create and sync a local env (writes uv.lock)
uv sync

# 2) Run the CLI from the project env
uv run thinkspace note "hello from uv"

# 3) Format & lint
uv run ruff check --select I --fix
uv run ruff format

# 4) Type checking
uv run mypy src

# 5) Tests
uv run pytest -q

# 6) Build & publish
uv build --no-sources
uv publish  # set UV_PUBLISH_TOKEN with a PyPI token
```

Dev dependencies live in `[dependency-groups]` and are synced by default.


## 📝 License

MIT © Thinkspace
