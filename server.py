#!/usr/bin/env python3
"""MCP server for Joplin, backed by the Joplin Web Clipper REST API."""

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

JOPLIN_BASE_URL = os.environ.get("JOPLIN_BASE_URL", "http://127.0.0.1:41184")
JOPLIN_TOKEN = os.environ.get("JOPLIN_TOKEN")

NOTE_LIST_FIELDS = "id,parent_id,title,updated_time,created_time,is_todo,todo_completed"
NOTE_FULL_FIELDS = NOTE_LIST_FIELDS + ",body,source_url"
RESOURCE_FIELDS = "id,title,mime,file_extension,size"
RESOURCE_OCR_FIELDS = "id,title,mime,ocr_status,ocr_text,ocr_error"

mcp = FastMCP("joplin")


def _client() -> httpx.Client:
    if not JOPLIN_TOKEN:
        raise RuntimeError(
            "JOPLIN_TOKEN is not set. Configure it in the MCP server's env block."
        )
    return httpx.Client(base_url=JOPLIN_BASE_URL, params={"token": JOPLIN_TOKEN}, timeout=15)


def _raise_for_joplin_error(resp: httpx.Response) -> None:
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"Joplin API error {resp.status_code}: {detail}")


@mcp.tool()
def list_notebooks() -> list[dict[str, Any]]:
    """List all Joplin notebooks (folders), with id, title and parent_id."""
    items: list[dict[str, Any]] = []
    page = 1
    with _client() as client:
        while True:
            resp = client.get("/folders", params={"fields": "id,title,parent_id", "page": page})
            _raise_for_joplin_error(resp)
            data = resp.json()
            items.extend(data.get("items", []))
            if not data.get("has_more"):
                break
            page += 1
    return items


@mcp.tool()
def create_notebook(title: str, parent_id: str | None = None) -> dict[str, Any]:
    """Create a new notebook (folder). Use parent_id to nest it under an
    existing notebook, e.g. a client/project notebook.

    Args:
        title: Notebook title.
        parent_id: Parent notebook (folder) id to nest under, if any.
    """
    payload: dict[str, Any] = {"title": title}
    if parent_id:
        payload["parent_id"] = parent_id
    with _client() as client:
        resp = client.post("/folders", json=payload)
        _raise_for_joplin_error(resp)
        return resp.json()


@mcp.tool()
def update_notebook(
    notebook_id: str,
    title: str | None = None,
    parent_id: str | None = None,
) -> dict[str, Any]:
    """Rename and/or move a notebook. Only the fields provided are changed.

    Args:
        notebook_id: The Joplin notebook (folder) id to edit.
        title: New title, if renaming it.
        parent_id: New parent notebook id, if moving it. Pass an empty string
            to move it to the top level (no parent).
    """
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if parent_id is not None:
        payload["parent_id"] = parent_id

    if not payload:
        raise ValueError("No fields provided to update.")

    with _client() as client:
        resp = client.put(f"/folders/{notebook_id}", json=payload)
        _raise_for_joplin_error(resp)
        return resp.json()


@mcp.tool()
def delete_notebook(notebook_id: str) -> str:
    """Delete a notebook by id, including all notes and sub-notebooks inside
    it. In Joplin this moves the notebook to the trash (or permanently
    deletes it if the trash is disabled in the app's settings).

    Args:
        notebook_id: The Joplin notebook (folder) id to delete.
    """
    with _client() as client:
        resp = client.delete(f"/folders/{notebook_id}")
        _raise_for_joplin_error(resp)
        return f"Notebook {notebook_id} deleted."


@mcp.tool()
def list_notes(notebook_id: str | None = None, limit: int = 50, page: int = 1) -> dict[str, Any]:
    """List notes, optionally filtered to a single notebook.

    Args:
        notebook_id: If set, only return notes inside this notebook (folder id).
        limit: Max notes per page (Joplin caps this at 100).
        page: Page number, starting at 1.
    """
    limit = max(1, min(limit, 100))
    with _client() as client:
        if notebook_id:
            resp = client.get(
                f"/folders/{notebook_id}/notes",
                params={"fields": NOTE_LIST_FIELDS, "limit": limit, "page": page},
            )
        else:
            resp = client.get(
                "/notes",
                params={"fields": NOTE_LIST_FIELDS, "limit": limit, "page": page},
            )
        _raise_for_joplin_error(resp)
        return resp.json()


@mcp.tool()
def search_notes(query: str, limit: int = 50, page: int = 1) -> dict[str, Any]:
    """Full-text search notes using Joplin's search syntax (e.g. 'title:foo', 'tag:bar').

    Args:
        query: Search query string.
        limit: Max results per page (Joplin caps this at 100).
        page: Page number, starting at 1.
    """
    limit = max(1, min(limit, 100))
    with _client() as client:
        resp = client.get(
            "/search",
            params={
                "query": query,
                "type": "note",
                "fields": NOTE_LIST_FIELDS,
                "limit": limit,
                "page": page,
            },
        )
        _raise_for_joplin_error(resp)
        return resp.json()


@mcp.tool()
def get_note(note_id: str) -> dict[str, Any]:
    """Fetch a single note's full content (including body) by id.

    Args:
        note_id: The Joplin note id.
    """
    with _client() as client:
        resp = client.get(f"/notes/{note_id}", params={"fields": NOTE_FULL_FIELDS})
        _raise_for_joplin_error(resp)
        return resp.json()


@mcp.tool()
def create_note(
    title: str,
    body: str = "",
    notebook_id: str | None = None,
    is_todo: bool = False,
) -> dict[str, Any]:
    """Create a new note.

    Args:
        title: Note title.
        body: Note body in Markdown.
        notebook_id: Target notebook (folder) id. If omitted, Joplin uses the
            currently selected notebook in the app.
        is_todo: If true, create the note as a to-do item.
    """
    payload: dict[str, Any] = {"title": title, "body": body, "is_todo": 1 if is_todo else 0}
    if notebook_id:
        payload["parent_id"] = notebook_id
    with _client() as client:
        resp = client.post("/notes", json=payload)
        _raise_for_joplin_error(resp)
        return resp.json()


@mcp.tool()
def update_note(
    note_id: str,
    title: str | None = None,
    body: str | None = None,
    notebook_id: str | None = None,
    is_todo: bool | None = None,
    todo_completed: bool | None = None,
) -> dict[str, Any]:
    """Edit an existing note. Only the fields provided are changed.

    Args:
        note_id: The Joplin note id to edit.
        title: New title, if changing it.
        body: New Markdown body, if changing it (replaces the whole body).
        notebook_id: Move the note to this notebook id, if changing it.
        is_todo: Convert to/from a to-do item, if changing it.
        todo_completed: Mark a to-do complete/incomplete, if changing it.
    """
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if notebook_id is not None:
        payload["parent_id"] = notebook_id
    if is_todo is not None:
        payload["is_todo"] = 1 if is_todo else 0
    if todo_completed is not None:
        payload["todo_completed"] = 1 if todo_completed else 0

    if not payload:
        raise ValueError("No fields provided to update.")

    with _client() as client:
        resp = client.put(f"/notes/{note_id}", json=payload)
        _raise_for_joplin_error(resp)
        return resp.json()


@mcp.tool()
def get_resource_info(resource_id: str) -> dict[str, Any]:
    """Fetch metadata for a Joplin resource (an attachment/image embedded in a
    note body, referenced there as ':/<resource_id>'), including its mime type
    and file extension. Use this before get_resource_file to pick a sensible
    file extension for the saved file.

    Args:
        resource_id: The Joplin resource id.
    """
    with _client() as client:
        resp = client.get(f"/resources/{resource_id}", params={"fields": RESOURCE_FIELDS})
        _raise_for_joplin_error(resp)
        return resp.json()


@mcp.tool()
def get_resource_file(resource_id: str, save_path: str) -> dict[str, Any]:
    """Download a Joplin resource's raw file (e.g. a screenshot embedded in a
    note) and save it to a local path, so it can then be viewed with a
    file-reading tool. Call get_resource_info first if you need the mime type
    to choose the save_path's extension.

    Args:
        resource_id: The Joplin resource id (from a note body link like ':/<id>').
        save_path: Absolute local file path to save the downloaded file to.
    """
    with _client() as client:
        resp = client.get(f"/resources/{resource_id}/file")
        _raise_for_joplin_error(resp)
        content = resp.content
    with open(save_path, "wb") as f:
        f.write(content)
    return {"saved_path": save_path, "size": len(content)}


@mcp.tool()
def get_resource_ocr_text(resource_id: str) -> dict[str, Any]:
    """Fetch the OCR-extracted text for a Joplin resource (e.g. text recognized
    inside a screenshot or scanned PDF/image attachment), without downloading
    the file itself. Requires Joplin's built-in OCR feature to be enabled
    (Options > General > "Enable document text extraction") and to have
    finished processing the resource.

    The returned `ocr_status` is one of: 0=not queued yet, 1=queued/todo,
    2=processing, 3=done, 4=error (see `ocr_error` if it failed). If OCR
    hasn't finished yet, retry after a short delay.

    Note: Joplin also automatically indexes ocr_text for full-text search,
    so search_notes may already surface hits found only inside an image via
    OCR without needing this tool.

    Args:
        resource_id: The Joplin resource id (from a note body link like ':/<id>').
    """
    with _client() as client:
        resp = client.get(f"/resources/{resource_id}", params={"fields": RESOURCE_OCR_FIELDS})
        _raise_for_joplin_error(resp)
        return resp.json()


@mcp.tool()
def delete_note(note_id: str) -> str:
    """Delete a note by id. In Joplin this moves the note to the trash (or
    permanently deletes it if the trash is disabled in the app's settings).

    Args:
        note_id: The Joplin note id to delete.
    """
    with _client() as client:
        resp = client.delete(f"/notes/{note_id}")
        _raise_for_joplin_error(resp)
        return f"Note {note_id} deleted."


if __name__ == "__main__":
    mcp.run()
