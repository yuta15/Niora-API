"""Workspace system preset CatalogをDatabaseへ投入する。"""

import argparse
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, cast
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.shared.infra.database import create_engine, create_session_factory
from src.shared.infra.settings import ApplicationDatabaseSettings
from src.workspace.domain import (
    TerminalExecAccessPoint,
    WorkspaceComponent,
    WorkspaceDefinition,
    WorkspacePreset,
    WorkspacePresetKey,
)
from src.workspace.infra.database import (
    PresetWorkspaceDefinitionMappingTable,
    TerminalAccessPointTable,
    WorkspaceComponentTable,
    WorkspaceDefinitionTable,
)

_SCHEMA_VERSION = 1
_DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[1] / "catalog/system/workspace/presets.json"
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkspacePresetCatalog:
    """差分処理へ渡す検証済みWorkspace preset Catalog。"""

    presets: tuple[WorkspacePreset, ...]


class WorkspacePresetCatalogLoader:
    """指定されたWorkspace Catalog JSONを検証済みCatalogへ変換する。"""

    def __init__(self, path: str | Path = _DEFAULT_CATALOG_PATH) -> None:
        self._path = Path(path)

    def load(self) -> WorkspacePresetCatalog:
        """Catalogを読み込む。Catalogの省略はDBの削除を意味しない。"""
        document_value = self._read_json()
        self._expect_keys(document_value, {"schema_version", "presets"}, json_path="$")
        document = cast(dict[str, object], document_value)

        schema_version = self._value(document, "schema_version", json_path="$")
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            self._fail("schema_version must be an integer", json_path="$.schema_version")
        if schema_version != _SCHEMA_VERSION:
            self._fail(
                f"unsupported schema_version {schema_version}; expected {_SCHEMA_VERSION}",
                json_path="$.schema_version",
            )

        preset_values = cast(
            list[object],
            self._value(document, "presets", json_path="$", expected=list),
        )
        return WorkspacePresetCatalog(self._load_presets(preset_values))

    def _load_presets(self, values: list[object]) -> tuple[WorkspacePreset, ...]:
        presets: list[WorkspacePreset] = []
        seen_preset_keys: set[WorkspacePresetKey] = set()
        seen_definition_ids: set[UUID] = set()

        for index, value in enumerate(values):
            preset = self._load_preset(value, index)
            if preset.preset_key in seen_preset_keys:
                self._fail(
                    "preset_key must be unique",
                    json_path=f"$.presets[{index}].preset_key",
                    index=index,
                )
            if preset.definition.definition_id in seen_definition_ids:
                self._fail(
                    "definition_id must be unique",
                    json_path=f"$.presets[{index}].definition.definition_id",
                    index=index,
                )
            seen_preset_keys.add(preset.preset_key)
            seen_definition_ids.add(preset.definition.definition_id)
            presets.append(preset)
        return tuple(presets)

    def _load_preset(self, value: object, index: int) -> WorkspacePreset:
        json_path = f"$.presets[{index}]"
        if not isinstance(value, dict):
            self._fail("preset must be an object", json_path=json_path, index=index)
        data = cast(dict[str, object], value)
        self._expect_keys(data, {"preset_key", "definition"}, json_path=json_path, index=index)

        preset_key_value = self._value(data, "preset_key", json_path=json_path)
        if not isinstance(preset_key_value, str):
            self._fail("preset_key must be a string", json_path=f"{json_path}.preset_key", index=index)
        try:
            preset_key = WorkspacePresetKey(preset_key_value)
        except (TypeError, ValueError) as error:
            self._fail(str(error), json_path=f"{json_path}.preset_key", index=index)

        definition = self._load_definition(
            self._value(data, "definition", json_path=json_path),
            json_path=f"{json_path}.definition",
            index=index,
        )
        return WorkspacePreset(preset_key=preset_key, definition=definition)

    def _load_definition(
        self,
        value: object,
        *,
        json_path: str,
        index: int,
    ) -> WorkspaceDefinition:
        if not isinstance(value, dict):
            self._fail("definition must be an object", json_path=json_path, index=index)
        data = cast(dict[str, object], value)
        self._expect_keys(data, {"definition_id", "components"}, json_path=json_path, index=index)

        definition_id_value = self._value(data, "definition_id", json_path=json_path)
        if not isinstance(definition_id_value, str):
            self._fail(
                "definition_id must be a UUID string",
                json_path=f"{json_path}.definition_id",
                index=index,
            )
        try:
            definition_id = UUID(definition_id_value)
        except ValueError:
            self._fail(
                "definition_id must be a UUID string",
                json_path=f"{json_path}.definition_id",
                index=index,
            )

        components = cast(
            list[object],
            self._value(data, "components", json_path=json_path, expected=list),
        )
        parsed_components = tuple(
            self._load_component(
                component,
                json_path=f"{json_path}.components[{component_index}]",
                index=component_index,
            )
            for component_index, component in enumerate(components)
        )
        try:
            return WorkspaceDefinition(definition_id=definition_id, components=parsed_components)
        except (TypeError, ValueError) as error:
            self._fail(str(error), json_path=f"{json_path}.components", index=index)

    def _load_component(
        self,
        value: object,
        *,
        json_path: str,
        index: int,
    ) -> WorkspaceComponent:
        if not isinstance(value, dict):
            self._fail("component must be an object", json_path=json_path, index=index)
        data = cast(dict[str, object], value)
        self._expect_keys(
            data,
            {"component_key", "image"},
            optional={"startup_command", "terminal_exec"},
            json_path=json_path,
            index=index,
        )
        component_key = self._string(data, "component_key", json_path=json_path, index=index)
        image = self._string(data, "image", json_path=json_path, index=index)
        startup_command = self._argv(data, "startup_command", json_path=json_path, index=index)
        terminal_exec = self._load_terminal_exec(data, json_path=json_path, index=index)
        try:
            return WorkspaceComponent(
                component_key=component_key,
                image=image,
                startup_command=startup_command,
                terminal_exec=terminal_exec,
            )
        except (TypeError, ValueError) as error:
            self._fail(str(error), json_path=json_path, index=index)

    def _load_terminal_exec(
        self,
        component: Mapping[str, object],
        *,
        json_path: str,
        index: int,
    ) -> TerminalExecAccessPoint | None:
        value = component.get("terminal_exec")
        if value is None:
            return None

        terminal_path = f"{json_path}.terminal_exec"
        if not isinstance(value, dict):
            self._fail("terminal_exec must be an object or null", json_path=terminal_path, index=index)
        terminal = cast(dict[str, object], value)
        self._expect_keys(terminal, {"command"}, json_path=terminal_path, index=index)
        command = self._argv(terminal, "command", json_path=terminal_path, index=index, required=True)
        assert command is not None
        try:
            return TerminalExecAccessPoint(command)
        except (TypeError, ValueError) as error:
            self._fail(str(error), json_path=f"{terminal_path}.command", index=index)

    def _argv(
        self,
        value: Mapping[str, object],
        name: str,
        *,
        json_path: str,
        index: int,
        required: bool = False,
    ) -> tuple[str, ...] | None:
        if name not in value:
            if required:
                self._fail(
                    f"missing required field {name}",
                    json_path=f"{json_path}.{name}",
                    index=index,
                )
            return None
        command = self._value(value, name, json_path=json_path)
        field_path = f"{json_path}.{name}"
        if command is None and not required:
            return None
        if not isinstance(command, list):
            self._fail("command must be an array of strings or null", json_path=field_path, index=index)
        if len(command) == 0:
            self._fail("command must contain at least one argument", json_path=field_path, index=index)
        parsed_arguments: list[str] = []
        for argument_index, argument in enumerate(command):
            if not isinstance(argument, str):
                self._fail(
                    "command arguments must be strings",
                    json_path=f"{field_path}[{argument_index}]",
                    index=argument_index,
                )
            parsed_arguments.append(argument)
        return tuple(parsed_arguments)

    def _string(self, value: Mapping[str, object], name: str, *, json_path: str, index: int) -> str:
        result = self._value(value, name, json_path=json_path)
        if not isinstance(result, str):
            self._fail("value must be a string", json_path=f"{json_path}.{name}", index=index)
        return result

    def _value(
        self,
        value: Mapping[str, object],
        name: str,
        *,
        json_path: str,
        expected: type | None = None,
    ) -> object:
        if name not in value:
            self._fail(f"missing required field {name}", json_path=f"{json_path}.{name}")
        result = value[name]
        if expected is not None and not isinstance(result, expected):
            self._fail(f"{name} must be a {expected.__name__}", json_path=f"{json_path}.{name}")
        return result

    def _expect_keys(
        self,
        value: object,
        expected: set[str],
        *,
        json_path: str,
        index: int | None = None,
        optional: set[str] | None = None,
    ) -> None:
        if not isinstance(value, dict):
            self._fail("value must be an object", json_path=json_path, index=index)
        allowed = expected | (optional or set())
        actual = set(value)
        missing = expected - actual
        extra = actual - allowed
        if missing:
            self._fail(
                f"missing required field(s): {', '.join(sorted(missing))}",
                json_path=json_path,
                index=index,
            )
        if extra:
            self._fail(
                f"unknown field(s): {', '.join(sorted(extra))}",
                json_path=json_path,
                index=index,
            )

    def _fail(self, message: str, *, json_path: str, index: int | None = None) -> NoReturn:
        index_text = f" index={index}" if index is not None else ""
        raise ValueError(f"workspace preset catalog error file={self._path} path={json_path}{index_text}: {message}")

    def _read_json(self) -> object:
        try:
            with self._path.open(encoding="utf-8") as catalog_file:
                return json.load(catalog_file)
        except OSError as error:
            raise ValueError(f"workspace preset catalog error file={self._path} path=$: {error}") from error
        except json.JSONDecodeError as error:
            raise ValueError(
                f"workspace preset catalog error file={self._path} path=$: "
                f"invalid JSON at line {error.lineno}, column {error.colno}"
            ) from error


@dataclass(frozen=True, slots=True)
class WorkspacePresetSeedPlan:
    """CatalogとDatabaseの差分をDB反映用に分類した計画。

    WorkspaceDefinitionは不変値として扱うため、更新対象は作らず、相違はDifferが競合として通知する。
    """

    definitions_to_insert: tuple[WorkspaceDefinition, ...]
    mappings_to_insert: tuple[WorkspacePreset, ...]
    unchanged_preset_keys: tuple[WorkspacePresetKey, ...]


@dataclass(slots=True)
class _StoredDefinitionState:
    """Database上のWorkspaceDefinitionと子要素。"""

    components: list[WorkspaceComponentTable]
    terminals_by_component_key: dict[str, TerminalAccessPointTable]


@dataclass(slots=True)
class _StoredWorkspacePresetState:
    """差分判定に必要なDatabase上のWorkspace preset状態。"""

    definitions_by_id: dict[UUID, _StoredDefinitionState]
    definition_id_by_preset_key: dict[str, UUID]
    preset_keys_by_definition_id: dict[UUID, set[str]]


class WorkspacePresetCatalogDiffer:
    """検証済みCatalogとDatabaseの現在値を比較してSeed計画を作成する。

    追加・変更不要を分類し、既存値の変更に相当する差分はValueErrorで通知する。
    """

    def create_plan(self, session: Session, catalog: WorkspacePresetCatalog) -> WorkspacePresetSeedPlan:
        """Catalogをinsert・unchangedに分類する。競合はValueErrorで通知する。"""
        presets = catalog.presets
        if not presets:
            return WorkspacePresetSeedPlan((), (), ())

        definitions = {preset.definition.definition_id: preset.definition for preset in presets}
        stored = self._load_stored_state(
            session,
            definition_ids=tuple(definitions),
            preset_keys=tuple(preset.preset_key.value for preset in presets),
        )
        self._validate_definitions(definitions, stored)
        self._validate_mappings(presets, stored)

        definitions_to_insert = tuple(
            definition
            for definition_id, definition in definitions.items()
            if definition_id not in stored.definitions_by_id
        )
        mappings_to_insert = tuple(
            preset for preset in presets if preset.preset_key.value not in stored.definition_id_by_preset_key
        )
        unchanged_preset_keys = tuple(
            preset.preset_key
            for preset in presets
            if preset.definition.definition_id in stored.definitions_by_id
            and preset.preset_key.value in stored.definition_id_by_preset_key
        )
        return WorkspacePresetSeedPlan(
            definitions_to_insert=definitions_to_insert,
            mappings_to_insert=mappings_to_insert,
            unchanged_preset_keys=unchanged_preset_keys,
        )

    def _load_stored_state(
        self,
        session: Session,
        *,
        definition_ids: tuple[UUID, ...],
        preset_keys: tuple[str, ...],
    ) -> _StoredWorkspacePresetState:
        existing_definition_ids = session.scalars(
            select(WorkspaceDefinitionTable.id).where(WorkspaceDefinitionTable.id.in_(definition_ids))
        ).all()
        existing_components = session.scalars(
            select(WorkspaceComponentTable).where(WorkspaceComponentTable.definition_id.in_(definition_ids))
        ).all()
        existing_terminals = session.scalars(
            select(TerminalAccessPointTable).where(TerminalAccessPointTable.definition_id.in_(definition_ids))
        ).all()
        existing_mappings = session.scalars(
            select(PresetWorkspaceDefinitionMappingTable).where(
                or_(
                    PresetWorkspaceDefinitionMappingTable.preset_key.in_(preset_keys),
                    PresetWorkspaceDefinitionMappingTable.definition_id.in_(definition_ids),
                )
            )
        ).all()

        definitions_by_id = {
            definition_id: _StoredDefinitionState(components=[], terminals_by_component_key={})
            for definition_id in existing_definition_ids
        }
        for component in existing_components:
            definitions_by_id[component.definition_id].components.append(component)
        for terminal in existing_terminals:
            definitions_by_id[terminal.definition_id].terminals_by_component_key[terminal.component_key] = terminal
        definition_id_by_preset_key = {mapping.preset_key: mapping.definition_id for mapping in existing_mappings}
        preset_keys_by_definition_id: dict[UUID, set[str]] = {}
        for mapping in existing_mappings:
            preset_keys_by_definition_id.setdefault(mapping.definition_id, set()).add(mapping.preset_key)
        return _StoredWorkspacePresetState(
            definitions_by_id=definitions_by_id,
            definition_id_by_preset_key=definition_id_by_preset_key,
            preset_keys_by_definition_id=preset_keys_by_definition_id,
        )

    def _validate_definitions(
        self,
        definitions: Mapping[UUID, WorkspaceDefinition],
        stored: _StoredWorkspacePresetState,
    ) -> None:
        for definition_id, expected_definition in definitions.items():
            stored_definition = stored.definitions_by_id.get(definition_id)
            if stored_definition is None:
                continue
            self._validate_components(
                definition_id,
                expected=expected_definition.components,
                stored=stored_definition.components,
            )
            self._validate_terminal_access_points(
                definition_id,
                expected_components=expected_definition.components,
                stored_terminals=stored_definition.terminals_by_component_key,
            )

    def _validate_components(
        self,
        definition_id: UUID,
        *,
        expected: tuple[WorkspaceComponent, ...],
        stored: list[WorkspaceComponentTable],
    ) -> None:
        stored_values = sorted(
            (
                component.component_key,
                component.position,
                component.image,
                self._normalize_json_value(component.startup_command),
            )
            for component in stored
        )
        expected_values = sorted(
            (
                component.component_key,
                position,
                component.image,
                self._normalize_json_value(component.startup_command),
            )
            for position, component in enumerate(expected)
        )
        if stored_values != expected_values:
            raise ValueError(
                f"workspace preset catalog conflict: definition components conflict: definition_id={definition_id}"
            )

    def _validate_terminal_access_points(
        self,
        definition_id: UUID,
        *,
        expected_components: tuple[WorkspaceComponent, ...],
        stored_terminals: Mapping[str, TerminalAccessPointTable],
    ) -> None:
        for component in expected_components:
            stored_terminal = stored_terminals.get(component.component_key)
            stored_command = None
            if stored_terminal is not None:
                stored_command = self._normalize_json_value(stored_terminal.command)

            expected_command = None
            if component.terminal_exec is not None:
                expected_command = component.terminal_exec.command

            if stored_command != expected_command:
                raise ValueError(
                    "workspace preset catalog conflict: "
                    f"component terminal conflicts: definition_id={definition_id} "
                    f"component_key={component.component_key}"
                )

        expected_component_keys = {component.component_key for component in expected_components}
        unknown_component_keys = set(stored_terminals) - expected_component_keys
        if unknown_component_keys:
            component_key = sorted(unknown_component_keys)[0]
            raise ValueError(
                "workspace preset catalog conflict: "
                f"terminal belongs to an unknown component: definition_id={definition_id} "
                f"component_key={component_key}"
            )

    def _validate_mappings(
        self,
        presets: tuple[WorkspacePreset, ...],
        stored: _StoredWorkspacePresetState,
    ) -> None:
        for preset in presets:
            expected_key = preset.preset_key.value
            expected_definition_id = preset.definition.definition_id
            stored_definition_id = stored.definition_id_by_preset_key.get(expected_key)
            if stored_definition_id is not None and stored_definition_id != expected_definition_id:
                raise ValueError(
                    "workspace preset catalog conflict: "
                    f"preset key is mapped to another definition: preset_key={expected_key}"
                )
            stored_preset_keys = stored.preset_keys_by_definition_id.get(expected_definition_id, set())
            if stored_preset_keys - {expected_key}:
                raise ValueError(
                    "workspace preset catalog conflict: "
                    f"definition is mapped to another preset key: definition_id={expected_definition_id}"
                )

    def _normalize_json_value(self, value: object) -> object:
        if isinstance(value, (list, tuple)):
            return tuple(self._normalize_json_value(item) for item in value)
        return value


class WorkspacePresetCatalogApplier:
    """Seed計画を呼び出し元Transactionへ適用する。"""

    def apply(self, session: Session, plan: WorkspacePresetSeedPlan) -> None:
        """Definition、Component、Terminal、Mappingの順にinsertする。"""
        for definition in plan.definitions_to_insert:
            session.add(WorkspaceDefinitionTable(id=definition.definition_id))
        session.flush()

        for definition in plan.definitions_to_insert:
            for position, component in enumerate(definition.components):
                session.add(
                    WorkspaceComponentTable(
                        definition_id=definition.definition_id,
                        component_key=component.component_key,
                        image=component.image,
                        position=position,
                        startup_command=component.startup_command,
                    )
                )
        session.flush()

        for definition in plan.definitions_to_insert:
            for component in definition.components:
                if component.terminal_exec is not None:
                    session.add(
                        TerminalAccessPointTable(
                            definition_id=definition.definition_id,
                            component_key=component.component_key,
                            command=component.terminal_exec.command,
                        )
                    )
        session.flush()

        for preset in plan.mappings_to_insert:
            session.add(
                PresetWorkspaceDefinitionMappingTable(
                    preset_key=preset.preset_key.value,
                    definition_id=preset.definition.definition_id,
                )
            )
        session.flush()


def _run(catalog_path: str | Path = _DEFAULT_CATALOG_PATH) -> WorkspacePresetSeedPlan:
    """Catalogを3段階で処理し、単一TransactionでApplication Databaseへ投入する。"""
    catalog = WorkspacePresetCatalogLoader(catalog_path).load()
    settings = ApplicationDatabaseSettings()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]
    engine = create_engine(settings)
    try:
        session_factory = create_session_factory(engine)
        with session_factory() as session, session.begin():
            plan = WorkspacePresetCatalogDiffer().create_plan(session, catalog)
            WorkspacePresetCatalogApplier().apply(session, plan)
        return plan
    finally:
        engine.dispose()


def _main(argv: list[str] | None = None) -> int:
    """CLIを実行し、終了Codeを返す。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=_DEFAULT_CATALOG_PATH,
        help="投入するWorkspace system preset Catalog JSONのPath",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        plan = _run(arguments.catalog)
    except Exception as error:
        _LOGGER.exception("seed_system_catalog failed: %s", error)
        return 1
    _LOGGER.info(
        "Seeded workspace system catalog from %s: definitions_inserted=%d mappings_inserted=%d unchanged=%d",
        arguments.catalog,
        len(plan.definitions_to_insert),
        len(plan.mappings_to_insert),
        len(plan.unchanged_preset_keys),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
