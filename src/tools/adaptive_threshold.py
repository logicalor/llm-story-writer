"""Adaptive scene critique threshold computation."""

from __future__ import annotations

from domain.value_objects.generation_settings import GenerationSettings


def compute_effective_threshold(
    settings: GenerationSettings,
    chapter_number: int,
    style_notes_first_chapter: int | None,
) -> float:
    """Return the effective critique threshold for the given chapter.

    In "fixed" mode returns ``settings.scene_critique_score_threshold`` unchanged.

    In "adaptive" mode the threshold starts at
    ``scene_critique_score_threshold - scene_critique_adaptive_slack`` for
    chapter 1 and increases linearly to ``scene_critique_score_threshold`` by
    ``style_notes_first_chapter``. If style notes have not appeared yet
    (``style_notes_first_chapter is None``) the floor value is used.
    """
    threshold = settings.scene_critique_score_threshold

    if settings.scene_critique_threshold_mode == "fixed":
        return threshold

    slack = settings.scene_critique_adaptive_slack
    floor = max(0.0, threshold - slack)

    if style_notes_first_chapter is None:
        return floor

    n = style_notes_first_chapter
    if n <= 1:
        return threshold

    progress = (chapter_number - 1) / (n - 1)
    effective = floor + (threshold - floor) * progress
    return min(threshold, effective)
