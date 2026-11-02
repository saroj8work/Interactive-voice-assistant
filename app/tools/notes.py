"""
Notes & Task Management Tool.
Saves notes, logs, and transcripts to disk with search and listing capabilities.
"""
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any
from app.config import settings
from app.tools.base import BaseTool, ToolResult


class NoteTool(BaseTool):
    name = "note_manager"
    description = "Creates, lists, reads, and searches local notes and memos."
    parameters_schema = {
        "action": {
            "type": "string",
            "description": "Action: 'create', 'list', 'search', or 'read'",
        },
        "content": {"type": "string", "description": "Note content to save"},
        "title": {"type": "string", "description": "Optional title for the note"},
        "query": {"type": "string", "description": "Search keyword for notes"},
    }

    def __init__(self, notes_dir: Path = None):
        self.notes_dir = notes_dir or settings.notes_dir
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.notes_dir / "notes_index.json"
        self._ensure_index()

    def _ensure_index(self):
        if not self.index_file.exists():
            self._save_index([])

    def _load_index(self) -> List[Dict[str, Any]]:
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_index(self, index: List[Dict[str, Any]]):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def execute(
        self,
        action: str = "create",
        content: str = "",
        title: str = "",
        query: str = "",
        **kwargs,
    ) -> ToolResult:
        act = action.lower()

        if act == "create" or (not act and content):
            if not content:
                return ToolResult(
                    success=False,
                    error="Content is required",
                    message="Please provide note content to save.",
                )

            now = datetime.datetime.now()
            note_id = now.strftime("%Y%m%d_%H%M%S")
            clean_title = (
                title.strip() if title else f"Note {now.strftime('%b %d, %H:%M')}"
            )
            filename = f"note_{note_id}.txt"
            filepath = self.notes_dir / filename

            # Write file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {clean_title}\nDate: {now.isoformat()}\n\n{content}\n")

            index = self._load_index()
            note_entry = {
                "id": note_id,
                "title": clean_title,
                "content": content[:120],
                "filename": filename,
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            }
            index.insert(0, note_entry)
            self._save_index(index)

            return ToolResult(
                success=True,
                data=note_entry,
                message=f"I've saved your note: '{clean_title}'.",
            )

        elif act == "list":
            index = self._load_index()
            if not index:
                return ToolResult(
                    success=True,
                    data=[],
                    message="You don't have any notes saved yet.",
                )

            summary = [f"• {n['title']} ({n['created_at']})" for n in index[:5]]
            list_text = "\n".join(summary)
            return ToolResult(
                success=True,
                data=index[:10],
                message=f"You have {len(index)} saved note(s):\n{list_text}",
            )

        elif act == "search":
            index = self._load_index()
            q = query.lower()
            matches = [
                n
                for n in index
                if q in n["title"].lower() or q in n["content"].lower()
            ]
            if not matches:
                return ToolResult(
                    success=True,
                    data=[],
                    message=f"No notes found matching '{query}'.",
                )

            return ToolResult(
                success=True,
                data=matches,
                message=f"Found {len(matches)} note(s) matching '{query}'.",
            )

        return ToolResult(
            success=False,
            error=f"Unknown action: {action}",
            message=f"Unsupported note action: {action}",
        )
