"""Verification tests for Issue #23 — Build Compaction Plugin.

Structural tests for the TypeScript OpenCode plugin at
.opencode/plugins/story-compaction.ts. Verifies file presence,
required hook registration, section headers, error handling,
path safety, token budgeting, and dependency hygiene.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PATH = PROJECT_ROOT / ".opencode" / "plugins" / "story-compaction.ts"


def _read_plugin() -> str:
    return PLUGIN_PATH.read_text(encoding="utf-8")


class TestCompactionPlugin:
    def test_plugin_file_exists(self) -> None:
        assert PLUGIN_PATH.exists(), f"Plugin file missing: {PLUGIN_PATH}"

    def test_plugin_contains_compacting_hook(self) -> None:
        content = _read_plugin()
        assert "experimental.session.compacting" in content

    def test_plugin_contains_required_sections(self) -> None:
        content = _read_plugin()
        required_sections = [
            "Story Continuity Context",
            "Current Position",
            "Story Direction",
            "Active Characters",
            "Active Plot Threads",
            "Recent Chapter Synopses",
        ]
        for section in required_sections:
            assert section in content, f"Missing section header: {section}"

    def test_plugin_default_export(self) -> None:
        content = _read_plugin()
        assert "export default" in content

    def test_plugin_graceful_degradation(self) -> None:
        content = _read_plugin()
        assert "try" in content
        assert re.search(r"\bcatch\b", content), "Missing catch block"

    def test_plugin_path_validation(self) -> None:
        content = _read_plugin()
        has_starts_with = "startsWith" in content
        has_is_within_base = "isWithinBase" in content
        assert has_starts_with or has_is_within_base, (
            "No path validation found (startsWith or isWithinBase)"
        )

    def test_plugin_token_budget(self) -> None:
        content = _read_plugin()
        assert "4000" in content, "Missing 4000 token budget reference"

    def test_plugin_no_external_dependencies(self) -> None:
        content = _read_plugin()
        import_matches = re.findall(
            r"""import\s+.*?\s+from\s+["']([^"']+)["']""", content
        )
        allowed_modules = {"fs", "path"}
        for module in import_matches:
            assert module in allowed_modules, (
                f"Unexpected external dependency: {module}"
            )

    def test_plugin_context_interface_defined(self) -> None:
        content = _read_plugin()
        assert re.search(
            r"interface\s+PluginContext\s*\{", content
        ), "Missing interface PluginContext"
        assert re.search(
            r"directory\?\s*:\s*string", content
        ), "PluginContext missing 'directory?: string'"
        assert re.search(
            r"worktree\?\s*:\s*string", content
        ), "PluginContext missing 'worktree?: string'"

    def test_compaction_input_interface_defined(self) -> None:
        content = _read_plugin()
        assert re.search(
            r"interface\s+CompactionInput\s*\{", content
        ), "Missing interface CompactionInput"

    def test_compaction_output_interface_defined(self) -> None:
        content = _read_plugin()
        assert re.search(
            r"interface\s+CompactionOutput\s*\{", content
        ), "Missing interface CompactionOutput"
        assert re.search(
            r"context\s*:\s*string\[\]", content
        ), "CompactionOutput missing 'context: string[]'"

    def test_plugin_export_uses_typed_parameters(self) -> None:
        content = _read_plugin()
        assert re.search(
            r"ctx\s*:\s*PluginContext", content
        ), "Plugin export not using PluginContext type"
        assert re.search(
            r"_input\s*:\s*CompactionInput", content
        ), "Plugin export not using CompactionInput type"
        assert re.search(
            r"output\s*:\s*CompactionOutput", content
        ), "Plugin export not using CompactionOutput type"
