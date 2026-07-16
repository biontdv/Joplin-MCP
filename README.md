# 📓 Joplin MCP Server

*A Model Context Protocol server that turns your [Joplin](https://joplinapp.org/) notebook into a tool an LLM can actually use — read, search, write, and organize notes, and pull OCR'd text straight out of your screenshots.*

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![MCP](https://img.shields.io/badge/protocol-MCP-8A2BE2)

---

## What is this?

[Joplin](https://joplinapp.org/) ships a local **Web Clipper / Data API** (`http://127.0.0.1:41184`) that can drive the whole app — notes, notebooks, tags, attachments — over plain HTTP.

This project wraps that API as an **[MCP](https://modelcontextprotocol.io/) server**, so any MCP-compatible client (Claude Code, Claude Desktop, or your own agent) can:

- Browse your notebook tree and list notes inside any notebook
- Read a note's full Markdown body
- Full-text search across your entire Joplin database
- Create, rename, move, and delete both notes **and** notebooks
- Download an embedded attachment (screenshot, PDF, PoC file, ...) to disk so it can be viewed
- **Pull OCR-extracted text out of an image/PDF attachment** — read what's *inside* a screenshot without ever opening it

No plugin needs to be installed inside Joplin itself — everything runs through the Data API that's already built in.

---

## Features

| Tool | What it does |
| --- | --- |
| `list_notebooks` | List every notebook (folder), with `id`, `title`, and `parent_id` |
| `create_notebook` | Create a new notebook, optionally nested under a parent |
| `update_notebook` | Rename and/or move a notebook to a different parent |
| `delete_notebook` | Delete a notebook, including everything inside it (moves it to Joplin's trash) |
| `list_notes` | List notes, optionally scoped to one notebook, paginated |
| `search_notes` | Full-text search using Joplin's native search syntax (`title:`, `tag:`, ...) |
| `get_note` | Fetch a note's full Markdown body + metadata |
| `create_note` | Create a new note (title, Markdown body, target notebook, to-do flag) |
| `update_note` | Rename, edit, and/or move a note (also edits body / to-do status) |
| `delete_note` | Delete a note (moves it to Joplin's trash) |
| `get_resource_info` | Get metadata (mime type, extension, size) for an attached file |
| `get_resource_file` | Download an attachment's raw bytes to a local path so it can be opened/viewed |
| `get_resource_ocr_text` | Read back the text Joplin's built-in OCR engine recognized inside an image/PDF attachment |

---

## Requirements

- **[Joplin desktop](https://joplinapp.org/download/)**, running, with the Web Clipper service enabled
- A Joplin **Web Clipper authorization token**
- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) — or plain `pip`

---

## Installation

```bash
git clone https://github.com/<your-username>/joplin-mcp.git
cd joplin-mcp

# with uv (recommended, uses the committed uv.lock for reproducible installs)
uv sync

# — or with plain pip —
pip install "httpx>=0.28.1" "mcp[cli]>=1.28.1"
```

### 1. Enable the Web Clipper service in Joplin

`Joplin → Tools → Options → Web Clipper` → turn it **on**. Note the port shown (default `41184`).

### 2. Grab your access token

Same screen → **"Advanced options"** → **"Copy token"**. Keep this secret — anyone with it has full read/write access to your entire notebook.

### 3. (Optional) Enable OCR, if you want `get_resource_ocr_text` to return anything

`Joplin → Tools → Options → General` → enable **"Enable document text extraction (OCR)"**. Joplin needs some time to process existing attachments after you turn this on — check the `ocr_status` field returned by the tool (`0`/`1` = queued, `2` = processing, `3` = done, `4` = error, see `ocr_error`).

---

## Configuration

The server reads two environment variables:

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `JOPLIN_TOKEN` | ✅ yes | — | Your Web Clipper authorization token |
| `JOPLIN_BASE_URL` | no | `http://127.0.0.1:41184` | Base URL of the Joplin Web Clipper API |

---

## Usage with an MCP client

Add this to your client's MCP config (e.g. `.mcp.json` for Claude Code, or the Claude Desktop config file):

```json
{
  "mcpServers": {
    "joplin": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/joplin-mcp", "python", "server.py"],
      "env": {
        "JOPLIN_TOKEN": "<your-joplin-web-clipper-token>",
        "JOPLIN_BASE_URL": "http://127.0.0.1:41184"
      }
    }
  }
}
```

> Running without `uv`? Swap `command`/`args` for `"command": "python", "args": ["/absolute/path/to/joplin-mcp/server.py"]` instead.

Restart/reconnect your MCP client and the `joplin` tools should show up.

---

## Example prompts once connected

- *"List my Joplin notebooks."*
- *"Search my notes for 'react devtools'."*
- *"Pull up the note titled X and summarize it."*
- *"Download the screenshot attached to this note so I can look at it."*
- *"What text was OCR'd out of that PDF I scanned last week?"*

---

## Security notes

- The Web Clipper token grants **full read/write access** to your entire Joplin database — treat it like a password. Never commit it to a repo.
- The server only talks to `127.0.0.1` by default (your local Joplin instance) — it's not designed to be exposed over a network.
- `delete_note` moves notes to Joplin's trash (recoverable), unless you've disabled the trash in Joplin's settings.

---

## Known limitations / roadmap

This covers the day-to-day note/notebook/attachment workflow, but doesn't (yet) wrap every corner of Joplin's Data API:

- ❌ Tags — no list/create/assign tag support
- ⚠️ Resources — no upload/delete of attachments (only read + OCR text)
- ❌ Note revision history

PRs welcome if you need one of these.

---

## Project structure

```
joplin-mcp/
├── server.py         # the MCP server — all tools live here
├── pyproject.toml    # project metadata + dependencies
├── uv.lock           # locked dependency versions (uv)
├── .python-version   # pinned Python version for uv
├── .gitignore
├── LICENSE
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE).
