import json
import re
from pathlib import Path

import pytest

from scripts.seed_system_catalog import WorkspacePresetCatalog, WorkspacePresetCatalogLoader, _main
from src.workspace.domain import WorkspacePresetKey

CATALOG_PATH = Path("catalog/system/workspace/presets.json")


def test_load_workspace_preset_catalog_success_loads_shipped_ubuntu_preset() -> None:
    """配布CatalogのUbuntu presetを検証済みCatalogへ変換できることを確認する。"""
    catalog = WorkspacePresetCatalogLoader(CATALOG_PATH).load()

    preset_key = WorkspacePresetKey("ws-ubuntu-24_04")
    preset = catalog.presets[0]

    assert isinstance(catalog, WorkspacePresetCatalog)
    assert tuple(item.preset_key for item in catalog.presets) == (preset_key,)
    assert preset.preset_key == preset_key
    assert str(preset.definition.definition_id) == "1f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5"
    assert len(preset.definition.components) == 1
    component = preset.definition.components[0]
    assert component.component_key == "main"
    assert component.image == "ubuntu:24.04"
    assert component.startup_command == ("sleep", "infinity")
    assert component.terminal_exec is not None
    assert component.terminal_exec.command == ("/bin/bash",)


def test_load_workspace_preset_catalog_success_allows_optional_component_fields(tmp_path: Path) -> None:
    """省略可能なargvとTerminal接続点を持つComponentを読み込めることを確認する。"""
    document = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    component = document["presets"][0]["definition"]["components"][0]
    component.pop("startup_command")
    component.pop("terminal_exec")
    optional_path = tmp_path / "optional.json"
    optional_path.write_text(json.dumps(document), encoding="utf-8")

    preset = WorkspacePresetCatalogLoader(optional_path).load().presets[0]

    assert preset.definition.components[0].startup_command is None
    assert preset.definition.components[0].terminal_exec is None


@pytest.mark.parametrize(
    ("path", "expected_path"),
    [
        ("presets[0].preset_key", "$.presets[0].preset_key"),
        ("components[0].image", "$.presets[0].definition.components[0].image"),
    ],
)
def test_load_workspace_preset_catalog_failure_reports_file_path_and_json_path(
    tmp_path: Path, path: str, expected_path: str
) -> None:
    """構造エラーにCatalog fileとJSON pathを含めることを確認する。"""
    document = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if path == "presets[0].preset_key":
        document["presets"][0]["preset_key"] = 42
    else:
        document["presets"][0]["definition"]["components"][0]["image"] = 42
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match=rf"file={re.escape(str(invalid_path))} path={re.escape(expected_path)}"):
        WorkspacePresetCatalogLoader(invalid_path).load()


def test_load_workspace_preset_catalog_failure_reports_array_index_for_duplicate_key(tmp_path: Path) -> None:
    """Domain整合性エラーにも配列indexを含めることを確認する。"""
    document = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    document["presets"].append(document["presets"][0])
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match=r"file=.* path=\$\.presets\[1\]\.preset_key index=1"):
        WorkspacePresetCatalogLoader(invalid_path).load()


def test_load_workspace_preset_catalog_failure_reports_invalid_json_location(tmp_path: Path) -> None:
    """JSON構文エラーにCatalog fileと行・列を含めることを確認する。"""
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text('{"schema_version": 1,', encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=rf"file={re.escape(str(invalid_path))} path=\$.*invalid JSON at line 1, column \d+",
    ):
        WorkspacePresetCatalogLoader(invalid_path).load()


def test_main_failure_reports_catalog_file_and_json_location(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """CLIからもCatalog構文エラーをログで確認できることを確認する。"""
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text('{"schema_version": 1,', encoding="utf-8")

    exit_code = _main(["--catalog", str(invalid_path)])

    standard_error = caplog.text
    assert exit_code == 1
    assert f"file={invalid_path} path=$" in standard_error
    assert "invalid JSON at line 1" in standard_error
