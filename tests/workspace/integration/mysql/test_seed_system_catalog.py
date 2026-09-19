import copy
import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy import Engine, delete, insert, select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from scripts.seed_system_catalog import (
    WorkspacePresetCatalog,
    WorkspacePresetCatalogApplier,
    WorkspacePresetCatalogDiffer,
    WorkspacePresetCatalogLoader,
    WorkspacePresetSeedPlan,
)
from src.workspace.infra.database import (
    PresetWorkspaceDefinitionMappingTable,
    TerminalAccessPointTable,
    WorkspaceComponentTable,
    WorkspaceDefinitionTable,
)

CATALOG_PATH = Path("catalog/system/workspace/presets.json")
SECOND_DEFINITION_ID = UUID("2f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5")
ROLLBACK_DEFINITION_ID = UUID("4f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5")
CASE_VARIANT_DEFINITION_ID = UUID("5f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5")


def _load_document() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _write_catalog(tmp_path: Path, document: dict[str, object], name: str = "catalog.json") -> WorkspacePresetCatalog:
    path = tmp_path / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return WorkspacePresetCatalogLoader(path).load()


def _seed_default(session: Session) -> WorkspacePresetSeedPlan:
    with session.begin():
        catalog = WorkspacePresetCatalogLoader(CATALOG_PATH).load()
        plan = WorkspacePresetCatalogDiffer().create_plan(session, catalog)
        WorkspacePresetCatalogApplier().apply(session, plan)
    return plan


@pytest.mark.integration
def test_seed_system_catalog_success_inserts_definition_components_terminal_and_mapping(
    mysql_session: Session,
) -> None:
    """初回投入でDefinition、Component、Terminal、Mappingを作成することを確認する。"""
    plan = _seed_default(mysql_session)

    assert len(plan.definitions_to_insert) == 1
    assert len(plan.mappings_to_insert) == 1
    assert plan.unchanged_preset_keys == ()
    assert len(mysql_session.scalars(select(WorkspaceDefinitionTable)).all()) == 1
    assert len(mysql_session.scalars(select(WorkspaceComponentTable)).all()) == 1
    assert len(mysql_session.scalars(select(TerminalAccessPointTable)).all()) == 1
    assert len(mysql_session.scalars(select(PresetWorkspaceDefinitionMappingTable)).all()) == 1
    mysql_session.rollback()


@pytest.mark.integration
def test_seed_system_catalog_success_is_noop_for_identical_catalog(mysql_session: Session) -> None:
    """同一Catalogの再投入で保存値が変わらないことを確認する。"""
    _seed_default(mysql_session)
    mysql_session.rollback()
    before = [
        (
            row.definition_id,
            row.component_key,
            row.image,
            row.position,
            row.startup_command,
        )
        for row in mysql_session.scalars(select(WorkspaceComponentTable)).all()
    ]
    mysql_session.rollback()

    plan = _seed_default(mysql_session)
    mysql_session.rollback()

    assert plan.definitions_to_insert == ()
    assert plan.mappings_to_insert == ()
    assert len(plan.unchanged_preset_keys) == 1

    after = [
        (
            row.definition_id,
            row.component_key,
            row.image,
            row.position,
            row.startup_command,
        )
        for row in mysql_session.scalars(select(WorkspaceComponentTable)).all()
    ]
    assert after == before


@pytest.mark.integration
def test_seed_system_catalog_success_adds_missing_mapping(mysql_session: Session) -> None:
    """Definition一式が存在してMappingだけ欠落した場合にMappingを追加することを確認する。"""
    _seed_default(mysql_session)
    mysql_session.execute(delete(PresetWorkspaceDefinitionMappingTable))
    mysql_session.commit()

    _seed_default(mysql_session)
    assert len(mysql_session.scalars(select(PresetWorkspaceDefinitionMappingTable)).all()) == 1
    mysql_session.rollback()


@pytest.mark.integration
def test_seed_system_catalog_failure_rejects_duplicate_definition_mapping(mysql_session: Session) -> None:
    """別preset_keyから同一definition_idへの直接INSERTをDBが拒否することを確認する。"""
    _seed_default(mysql_session)

    with pytest.raises(IntegrityError):
        mysql_session.execute(
            insert(PresetWorkspaceDefinitionMappingTable).values(
                preset_key="ws-duplicate-definition",
                definition_id=UUID("1f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5"),
            )
        )

    mysql_session.rollback()


@pytest.mark.integration
def test_seed_system_catalog_failure_rolls_back_new_rows_on_definition_conflict(
    mysql_session: Session, tmp_path: Path
) -> None:
    """Definition構成競合時にCatalog内の後続Definitionも追加されないことを確認する。"""
    _seed_default(mysql_session)
    mysql_session.rollback()
    document = _load_document()
    first_preset = copy.deepcopy(document["presets"][0])
    first_preset["definition"]["components"][0]["image"] = "ubuntu:22.04"
    second_preset = copy.deepcopy(document["presets"][0])
    second_preset["preset_key"] = "ws-second"
    second_preset["definition"]["definition_id"] = str(SECOND_DEFINITION_ID)
    document["presets"] = [first_preset, second_preset]

    with pytest.raises(ValueError, match="workspace preset catalog conflict"):
        with mysql_session.begin():
            catalog = _write_catalog(tmp_path, document)
            plan = WorkspacePresetCatalogDiffer().create_plan(mysql_session, catalog)
            WorkspacePresetCatalogApplier().apply(mysql_session, plan)

    mysql_session.rollback()
    assert mysql_session.get(WorkspaceDefinitionTable, SECOND_DEFINITION_ID) is None


@pytest.mark.integration
def test_seed_system_catalog_failure_rolls_back_definition_after_component_insert_fails(
    mysql_session: Session, tmp_path: Path
) -> None:
    """Definition INSERT後のComponent image保存失敗で全行がrollbackされることを確認する。"""
    document = _load_document()
    document["presets"][0]["preset_key"] = "ws-rollback"
    definition = document["presets"][0]["definition"]
    definition["definition_id"] = str(ROLLBACK_DEFINITION_ID)

    with pytest.raises(DataError):
        with mysql_session.begin():
            catalog = _write_catalog(tmp_path, document)
            plan = WorkspacePresetCatalogDiffer().create_plan(mysql_session, catalog)
            WorkspacePresetCatalogApplier().apply(mysql_session, plan)
            mysql_session.add(
                WorkspaceComponentTable(
                    definition_id=ROLLBACK_DEFINITION_ID,
                    component_key="invalid-image",
                    image="x" * 513,
                    position=1,
                    startup_command=None,
                )
            )
            mysql_session.flush()

    engine = cast(Engine, mysql_session.get_bind())
    with engine.connect() as connection:
        stored_definition_id = connection.scalar(
            select(WorkspaceDefinitionTable.id).where(WorkspaceDefinitionTable.id == ROLLBACK_DEFINITION_ID)
        )
    assert stored_definition_id is None


@pytest.mark.integration
def test_seed_system_catalog_success_accepts_case_distinct_preset_keys(mysql_session: Session, tmp_path: Path) -> None:
    """大文字小文字だけが異なるpreset_keyを同一Catalogから保存できることを確認する。"""
    document = _load_document()
    first_preset = copy.deepcopy(document["presets"][0])
    first_preset["preset_key"] = "ws-A"
    second_preset = copy.deepcopy(document["presets"][0])
    second_preset["preset_key"] = "ws-a"
    second_preset["definition"]["definition_id"] = str(SECOND_DEFINITION_ID)
    document["presets"] = [first_preset, second_preset]

    with mysql_session.begin():
        catalog = _write_catalog(tmp_path, document)
        plan = WorkspacePresetCatalogDiffer().create_plan(mysql_session, catalog)
        WorkspacePresetCatalogApplier().apply(mysql_session, plan)

    preset_keys = set(mysql_session.scalars(select(PresetWorkspaceDefinitionMappingTable.preset_key)).all())
    assert preset_keys == {"ws-A", "ws-a"}


@pytest.mark.integration
def test_seed_system_catalog_success_persists_512_character_preset_key(mysql_session: Session, tmp_path: Path) -> None:
    """512文字のpreset_keyをMySQLへseedし同じ値で取得できることを確認する。"""
    document = _load_document()
    preset_key = "a" * 512
    document["presets"][0]["preset_key"] = preset_key

    with mysql_session.begin():
        catalog = _write_catalog(tmp_path, document)
        plan = WorkspacePresetCatalogDiffer().create_plan(mysql_session, catalog)
        WorkspacePresetCatalogApplier().apply(mysql_session, plan)

    mapping = mysql_session.get(PresetWorkspaceDefinitionMappingTable, preset_key)

    assert mapping is not None
    assert mapping.preset_key == preset_key


@pytest.mark.integration
def test_seed_system_catalog_success_accepts_case_distinct_components_and_terminals(
    mysql_session: Session, tmp_path: Path
) -> None:
    """同一Definition内の大文字小文字が異なるComponentとTerminalを保存できることを確認する。"""
    document = _load_document()
    preset = document["presets"][0]
    preset["definition"]["definition_id"] = str(CASE_VARIANT_DEFINITION_ID)
    first_component = preset["definition"]["components"][0]
    first_component["component_key"] = "component-A"
    second_component = copy.deepcopy(first_component)
    second_component["component_key"] = "component-a"
    preset["definition"]["components"] = [first_component, second_component]

    with mysql_session.begin():
        catalog = _write_catalog(tmp_path, document)
        plan = WorkspacePresetCatalogDiffer().create_plan(mysql_session, catalog)
        WorkspacePresetCatalogApplier().apply(mysql_session, plan)

    component_keys = set(
        mysql_session.scalars(
            select(WorkspaceComponentTable.component_key).where(
                WorkspaceComponentTable.definition_id == CASE_VARIANT_DEFINITION_ID
            )
        ).all()
    )
    terminal_keys = set(
        mysql_session.scalars(
            select(TerminalAccessPointTable.component_key).where(
                TerminalAccessPointTable.definition_id == CASE_VARIANT_DEFINITION_ID
            )
        ).all()
    )
    assert component_keys == {"component-A", "component-a"}
    assert terminal_keys == {"component-A", "component-a"}


@pytest.mark.integration
def test_seed_system_catalog_success_preserves_rows_omitted_from_catalog(mysql_session: Session) -> None:
    """Catalogから省略した既存DefinitionとMappingを削除しないことを確認する。"""
    _seed_default(mysql_session)
    omitted_definition_id = UUID("3f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5")
    with mysql_session.begin():
        mysql_session.add(WorkspaceDefinitionTable(id=omitted_definition_id))
        mysql_session.flush()
        mysql_session.add(
            WorkspaceComponentTable(
                definition_id=omitted_definition_id,
                component_key="omitted",
                image="busybox:latest",
                position=0,
                startup_command=None,
            )
        )
        mysql_session.add(
            PresetWorkspaceDefinitionMappingTable(
                preset_key="ws-omitted",
                definition_id=omitted_definition_id,
            )
        )
    mysql_session.rollback()

    _seed_default(mysql_session)
    mysql_session.rollback()
    assert mysql_session.get(WorkspaceDefinitionTable, omitted_definition_id) is not None
    assert mysql_session.get(PresetWorkspaceDefinitionMappingTable, "ws-omitted") is not None
