"""Typed pipeline handoff objects for the Python-native orchestration layer.

Each dataclass represents the structured payload passed between
pipeline phases. Phase-to-phase communication uses typed objects —
not free-form text or chat histories.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class OutlineResult:
    """Structured outline produced by the Outline phase.

    Produced by: Outline phase (outline-planner agent)
    Consumed by: Narrative Arc Analysis, Character Sheets, and Settings phases
    """

    story_name: str
    chapter_outlines: list[dict[str, Any]]
    summary: str
    genre: str
    themes: list[str]
    savepoint_id: str | None = None


@dataclass
class ChapterDraft:
    """A drafted chapter produced by the Chapter Loop phase.

    Produced by: Chapter Loop phase (chapter-writer agent)
    Consumed by: Quality Reviewer and Final Edit phases
    """

    story_name: str
    chapter_number: int
    title: str
    content: str
    word_count: int
    savepoint_id: str | None = None


@dataclass
class WikiUpdateBatch:
    """A batch of wiki page updates produced after a chapter is written.

    Produced by: Wiki Maintainer (invoked after each chapter in the Chapter Loop)
    Consumed by: Wiki storage layer (ChromaDB + on-disk JSON pages)
    """

    story_name: str
    chapter_number: int
    updated_pages: list[str]  # page names (slugs) that were updated
    new_pages: list[str]  # page names (slugs) that were created
    savepoint_id: str | None = None


@dataclass
class ApprovalDecision:
    """The outcome of a human (or batch auto-proceed) approval gate.

    Produced by: Approval gate (TUI input widget or batch null-gate)
    Consumed by: Pipeline orchestrator to determine whether to proceed, revise, or reject
    """

    approved: bool
    feedback: str | None = None  # revision notes if not approved
    auto_approved: bool = False  # True when batch mode resolved the gate automatically


@dataclass
class PipelineState:
    """Full persisted state of a running pipeline run.

    Produced by: Pipeline orchestrator (maintained across all phases)
    Consumed by: All pipeline phases (read current phase/status); savepoint system (read/write JSON)

    Supports JSON serialisation for savepoint persistence via to_dict() / from_dict().
    """

    story_name: str
    current_phase: str
    completed_phases: list[str] = field(default_factory=list)
    outline_result: OutlineResult | None = None
    approved_chapters: list[ChapterDraft] = field(default_factory=list)
    wiki_batches: list[WikiUpdateBatch] = field(default_factory=list)
    batch_mode: bool = False
    savepoint_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict for savepoint persistence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineState:
        """Reconstruct a PipelineState from a previously serialised dict."""
        outline_data = data.get("outline_result")
        outline = OutlineResult(**outline_data) if outline_data is not None else None
        approved_chapters = [
            ChapterDraft(**ch) for ch in data.get("approved_chapters", [])
        ]
        wiki_batches = [WikiUpdateBatch(**wb) for wb in data.get("wiki_batches", [])]
        return cls(
            story_name=data["story_name"],
            current_phase=data["current_phase"],
            completed_phases=data.get("completed_phases", []),
            outline_result=outline,
            approved_chapters=approved_chapters,
            wiki_batches=wiki_batches,
            batch_mode=data.get("batch_mode", False),
            savepoint_id=data.get("savepoint_id"),
        )

    def to_json(self) -> str:
        """Serialise to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
