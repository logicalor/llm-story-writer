"""Verification tests for Issue #100 - rag_service dead code removal."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = str(PROJECT_ROOT / "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


from application.strategies.outline_chapter.strategy import OutlineChapterStrategy
from application.strategies.outline_chapter.outline_generator import OutlineGenerator
from application.strategies.outline_chapter.chapter_generator import ChapterGenerator
from application.strategies.outline_chapter.character_manager import CharacterManager
from application.strategies.outline_chapter.recap_manager import RecapManager
from application.strategies.outline_chapter.scene_generator import SceneGenerator
from application.strategies.outline_chapter.setting_manager import SettingManager
from application.strategies.outline_chapter.story_state_manager import StoryStateManager
from application.strategies.strategy_factory import StrategyFactory


def test_outline_chapter_strategy_excludes_rag_service_param() -> None:
    parameters = inspect.signature(OutlineChapterStrategy.__init__).parameters

    assert "rag_service" not in parameters


def test_outline_generator_excludes_rag_service_param() -> None:
    parameters = inspect.signature(OutlineGenerator.__init__).parameters

    assert "rag_service" not in parameters


def test_chapter_generator_excludes_rag_service_param() -> None:
    parameters = inspect.signature(ChapterGenerator.__init__).parameters

    assert "rag_service" not in parameters


def test_character_manager_excludes_rag_service_param() -> None:
    parameters = inspect.signature(CharacterManager.__init__).parameters

    assert "rag_service" not in parameters


def test_recap_manager_excludes_rag_service_param() -> None:
    parameters = inspect.signature(RecapManager.__init__).parameters

    assert "rag_service" not in parameters


def test_scene_generator_excludes_rag_service_param() -> None:
    parameters = inspect.signature(SceneGenerator.__init__).parameters

    assert "rag_service" not in parameters


def test_setting_manager_excludes_rag_service_param() -> None:
    parameters = inspect.signature(SettingManager.__init__).parameters

    assert "rag_service" not in parameters


def test_story_state_manager_excludes_rag_service_param() -> None:
    parameters = inspect.signature(StoryStateManager.__init__).parameters

    assert "rag_service" not in parameters


def test_strategy_factory_create_strategy_with_prompts_excludes_rag_service() -> None:
    parameters = inspect.signature(
        StrategyFactory.create_strategy_with_prompts
    ).parameters

    assert "rag_service" not in parameters


def test_outline_chapter_strategy_dead_rag_methods_removed() -> None:
    removed_methods = [
        "_initialize_rag_story",
        "_purge_story_rag_content",
        "get_rag_story_id",
        "has_rag_story",
        "get_rag_status",
    ]

    for method_name in removed_methods:
        assert not hasattr(OutlineChapterStrategy, method_name)