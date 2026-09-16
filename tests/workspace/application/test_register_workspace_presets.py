from uuid import UUID

import pytest

from src.shared.application.ports import UnitOfWork
from src.workspace.application import WorkspacePresetConflictError
from src.workspace.application.ports import WorkspaceDefinitionRepository, WorkspacePresetRepository
from src.workspace.application.usecases import RegisterWorkspacePresets
from src.workspace.domain import (
    TerminalExecAccessPoint,
    WorkspaceComponent,
    WorkspaceDefinition,
    WorkspacePreset,
    WorkspacePresetKey,
    WorkspacePresetProvider,
)

FIRST_PRESET_KEY = WorkspacePresetKey("ws-first")
SECOND_PRESET_KEY = WorkspacePresetKey("ws-second")
EXISTING_PRESET_KEY = WorkspacePresetKey("ws-existing")
FIRST_DEFINITION_ID = UUID("10000000-0000-0000-0000-000000000001")
SECOND_DEFINITION_ID = UUID("10000000-0000-0000-0000-000000000002")
EXISTING_DEFINITION_ID = UUID("10000000-0000-0000-0000-000000000003")


def _definition(
    definition_id: UUID,
    *,
    image: str,
    startup_command: tuple[str, ...] | None = None,
    terminal_command: tuple[str, ...] | None = None,
) -> WorkspaceDefinition:
    terminal_exec = None
    if terminal_command is not None:
        terminal_exec = TerminalExecAccessPoint(terminal_command)

    return WorkspaceDefinition(
        definition_id=definition_id,
        components=(
            WorkspaceComponent(
                component_key="application",
                image=image,
                startup_command=startup_command,
                terminal_exec=terminal_exec,
            ),
            WorkspaceComponent(component_key="database", image="mysql:9.7"),
        ),
    )


def _provider(presets: tuple[tuple[WorkspacePresetKey, WorkspaceDefinition], ...]) -> WorkspacePresetProvider:
    return WorkspacePresetProvider(
        preset_keys=tuple(preset_key for preset_key, _ in presets),
        definitions=tuple(definition for _, definition in presets),
        definition_ids_by_preset_key={preset_key: definition.definition_id for preset_key, definition in presets},
    )


def _definition_signature(definition: WorkspaceDefinition) -> tuple[object, ...]:
    component_signatures: list[tuple[object, ...]] = []
    for component in definition.components:
        terminal_command = None
        if component.terminal_exec is not None:
            terminal_command = component.terminal_exec.command
        component_signatures.append(
            (
                component.component_key,
                component.image,
                component.startup_command,
                terminal_command,
            )
        )

    return definition.definition_id, tuple(component_signatures)


class FakeWorkspaceCatalogRepository(WorkspacePresetRepository, WorkspaceDefinitionRepository):
    """CatalogのTransaction内変更をstagingで保持するFake。"""

    def __init__(self, presets: tuple[WorkspacePreset, ...] = ()) -> None:
        self.definitions = {preset.definition.definition_id: preset.definition for preset in presets}
        self.definition_ids_by_preset_key = {preset.preset_key: preset.definition.definition_id for preset in presets}
        self.received_presets: list[WorkspacePreset] = []
        self._staged_definitions: dict[UUID, WorkspaceDefinition] | None = None
        self._staged_definition_ids_by_preset_key: dict[WorkspacePresetKey, UUID] | None = None

    def register(self, preset: WorkspacePreset) -> None:
        self.received_presets.append(preset)
        self._start_staging()
        assert self._staged_definitions is not None
        assert self._staged_definition_ids_by_preset_key is not None

        definition_id = preset.definition.definition_id
        existing_definition = self._staged_definitions.get(definition_id)
        if existing_definition is not None:
            if _definition_signature(existing_definition) != _definition_signature(preset.definition):
                raise WorkspacePresetConflictError(preset.preset_key, definition_id)

        existing_definition_id = self._staged_definition_ids_by_preset_key.get(preset.preset_key)
        if existing_definition_id is not None and existing_definition_id != definition_id:
            raise WorkspacePresetConflictError(preset.preset_key, definition_id)

        for existing_preset_key, existing_definition_id in self._staged_definition_ids_by_preset_key.items():
            if existing_definition_id == definition_id and existing_preset_key != preset.preset_key:
                raise WorkspacePresetConflictError(preset.preset_key, definition_id)

        self._staged_definitions[definition_id] = preset.definition
        self._staged_definition_ids_by_preset_key[preset.preset_key] = definition_id

    def get(self, definition_id: UUID) -> WorkspaceDefinition | None:
        definitions = self.definitions
        if self._staged_definitions is not None:
            definitions = self._staged_definitions
        return definitions.get(definition_id)

    def commit(self) -> None:
        if self._staged_definitions is not None:
            self.definitions = self._staged_definitions
        if self._staged_definition_ids_by_preset_key is not None:
            self.definition_ids_by_preset_key = self._staged_definition_ids_by_preset_key
        self._clear_staging()

    def rollback(self) -> None:
        self._clear_staging()

    def _start_staging(self) -> None:
        if self._staged_definitions is not None:
            return
        self._staged_definitions = dict(self.definitions)
        self._staged_definition_ids_by_preset_key = dict(self.definition_ids_by_preset_key)

    def _clear_staging(self) -> None:
        self._staged_definitions = None
        self._staged_definition_ids_by_preset_key = None


class FailingWorkspacePresetRepository(WorkspacePresetRepository):
    """指定したPresetの保存だけに失敗するFake。"""

    def __init__(
        self,
        repository: FakeWorkspaceCatalogRepository,
        failing_preset_key: WorkspacePresetKey,
    ) -> None:
        self._repository = repository
        self._failing_preset_key = failing_preset_key

    def register(self, preset: WorkspacePreset) -> None:
        if preset.preset_key == self._failing_preset_key:
            raise RuntimeError("workspace preset persistence failed")
        self._repository.register(preset)


class FakeUnitOfWork(UnitOfWork):
    """Fake RepositoryのstagingをcommitまたはrollbackするUnitOfWork。"""

    def __init__(self, repository: FakeWorkspaceCatalogRepository) -> None:
        self._repository = repository
        self.commit_call_count = 0
        self.rollback_call_count = 0

    def _commit(self) -> None:
        self.commit_call_count += 1
        self._repository.commit()

    def _rollback(self) -> None:
        self.rollback_call_count += 1
        self._repository.rollback()


def test_execute_success_registers_all_presets_and_commits_catalog() -> None:
    """全Presetを定義順に登録し、既存項目を残したままCatalog全体をcommitすることを確認する。"""
    first_definition = _definition(
        FIRST_DEFINITION_ID,
        image="application:first",
        startup_command=("run", "first"),
        terminal_command=("/bin/sh",),
    )
    second_definition = _definition(SECOND_DEFINITION_ID, image="application:second")
    existing_preset = WorkspacePreset(
        preset_key=EXISTING_PRESET_KEY,
        definition=_definition(EXISTING_DEFINITION_ID, image="application:existing"),
    )
    repository = FakeWorkspaceCatalogRepository((existing_preset,))
    unit_of_work = FakeUnitOfWork(repository)

    RegisterWorkspacePresets(
        _provider(((FIRST_PRESET_KEY, first_definition), (SECOND_PRESET_KEY, second_definition))),
        repository,
        unit_of_work,
    ).execute()

    assert [preset.preset_key for preset in repository.received_presets] == [
        FIRST_PRESET_KEY,
        SECOND_PRESET_KEY,
    ]
    assert repository.definition_ids_by_preset_key == {
        EXISTING_PRESET_KEY: EXISTING_DEFINITION_ID,
        FIRST_PRESET_KEY: FIRST_DEFINITION_ID,
        SECOND_PRESET_KEY: SECOND_DEFINITION_ID,
    }
    assert _definition_signature(repository.definitions[FIRST_DEFINITION_ID]) == _definition_signature(first_definition)
    assert _definition_signature(repository.definitions[SECOND_DEFINITION_ID]) == _definition_signature(
        second_definition
    )
    assert unit_of_work.commit_call_count == 1
    assert unit_of_work.rollback_call_count == 0


def test_execute_success_is_idempotent_for_identical_catalog() -> None:
    """同一Catalogを再登録しても永続化内容を変更せずcommitできることを確認する。"""
    definition = _definition(
        FIRST_DEFINITION_ID,
        image="application:first",
        startup_command=("run", "first"),
        terminal_command=("/bin/bash", "-l"),
    )
    provider = _provider(((FIRST_PRESET_KEY, definition),))
    repository = FakeWorkspaceCatalogRepository()
    unit_of_work = FakeUnitOfWork(repository)
    usecase = RegisterWorkspacePresets(provider, repository, unit_of_work)

    usecase.execute()
    first_registration = _definition_signature(repository.definitions[FIRST_DEFINITION_ID])
    usecase.execute()

    assert _definition_signature(repository.definitions[FIRST_DEFINITION_ID]) == first_registration
    assert repository.definition_ids_by_preset_key == {FIRST_PRESET_KEY: FIRST_DEFINITION_ID}
    assert unit_of_work.commit_call_count == 2
    assert unit_of_work.rollback_call_count == 0


def test_execute_failure_raises_conflict_for_changed_definition_with_same_id() -> None:
    """同一Definition IDの全構成値が一致しない場合に入力を特定できる競合を送出することを確認する。"""
    existing_preset = WorkspacePreset(
        preset_key=FIRST_PRESET_KEY,
        definition=_definition(
            FIRST_DEFINITION_ID,
            image="application:first",
            terminal_command=("/bin/sh",),
        ),
    )
    changed_definition = _definition(
        FIRST_DEFINITION_ID,
        image="application:first",
        terminal_command=("/bin/bash",),
    )
    repository = FakeWorkspaceCatalogRepository((existing_preset,))
    unit_of_work = FakeUnitOfWork(repository)

    with pytest.raises(WorkspacePresetConflictError, match="ws-first") as exception_info:
        RegisterWorkspacePresets(
            _provider(((FIRST_PRESET_KEY, changed_definition),)),
            repository,
            unit_of_work,
        ).execute()

    assert exception_info.value.preset_key == FIRST_PRESET_KEY
    assert exception_info.value.definition_id == FIRST_DEFINITION_ID
    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


def test_execute_failure_raises_conflict_when_preset_key_is_reassigned() -> None:
    """既存Preset keyを別Definition IDへ付け替える登録を拒否することを確認する。"""
    existing_preset = WorkspacePreset(
        preset_key=FIRST_PRESET_KEY,
        definition=_definition(FIRST_DEFINITION_ID, image="application:first"),
    )
    reassigned_definition = _definition(SECOND_DEFINITION_ID, image="application:second")
    repository = FakeWorkspaceCatalogRepository((existing_preset,))
    unit_of_work = FakeUnitOfWork(repository)

    with pytest.raises(WorkspacePresetConflictError) as exception_info:
        RegisterWorkspacePresets(
            _provider(((FIRST_PRESET_KEY, reassigned_definition),)),
            repository,
            unit_of_work,
        ).execute()

    assert exception_info.value.preset_key == FIRST_PRESET_KEY
    assert exception_info.value.definition_id == SECOND_DEFINITION_ID
    assert repository.definition_ids_by_preset_key == {FIRST_PRESET_KEY: FIRST_DEFINITION_ID}
    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


def test_execute_failure_raises_conflict_when_definition_id_is_reassigned() -> None:
    """既存Definition IDを別Preset keyへ再対応付けする登録を拒否することを確認する。"""
    definition = _definition(FIRST_DEFINITION_ID, image="application:first")
    existing_preset = WorkspacePreset(
        preset_key=EXISTING_PRESET_KEY,
        definition=definition,
    )
    repository = FakeWorkspaceCatalogRepository((existing_preset,))
    unit_of_work = FakeUnitOfWork(repository)

    with pytest.raises(WorkspacePresetConflictError) as exception_info:
        RegisterWorkspacePresets(
            _provider(((FIRST_PRESET_KEY, definition),)),
            repository,
            unit_of_work,
        ).execute()

    assert exception_info.value.preset_key == FIRST_PRESET_KEY
    assert exception_info.value.definition_id == FIRST_DEFINITION_ID
    assert repository.definition_ids_by_preset_key == {EXISTING_PRESET_KEY: FIRST_DEFINITION_ID}
    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


def test_execute_failure_rolls_back_entire_catalog_when_later_preset_conflicts() -> None:
    """複数Presetの途中で競合した場合に先行登録を含むCatalog全体をrollbackすることを確認する。"""
    existing_preset = WorkspacePreset(
        preset_key=SECOND_PRESET_KEY,
        definition=_definition(SECOND_DEFINITION_ID, image="application:existing"),
    )
    first_definition = _definition(FIRST_DEFINITION_ID, image="application:first")
    conflicting_definition = _definition(SECOND_DEFINITION_ID, image="application:changed")
    repository = FakeWorkspaceCatalogRepository((existing_preset,))
    unit_of_work = FakeUnitOfWork(repository)

    with pytest.raises(WorkspacePresetConflictError):
        RegisterWorkspacePresets(
            _provider(
                (
                    (FIRST_PRESET_KEY, first_definition),
                    (SECOND_PRESET_KEY, conflicting_definition),
                )
            ),
            repository,
            unit_of_work,
        ).execute()

    assert FIRST_DEFINITION_ID not in repository.definitions
    assert repository.definition_ids_by_preset_key == {SECOND_PRESET_KEY: SECOND_DEFINITION_ID}
    assert [preset.preset_key for preset in repository.received_presets] == [
        FIRST_PRESET_KEY,
        SECOND_PRESET_KEY,
    ]
    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


def test_execute_failure_rolls_back_entire_catalog_when_later_persistence_fails() -> None:
    """複数Presetの途中で保存に失敗した場合に先行登録を含むCatalog全体をrollbackすることを確認する。"""
    first_definition = _definition(FIRST_DEFINITION_ID, image="application:first")
    second_definition = _definition(SECOND_DEFINITION_ID, image="application:second")
    repository = FakeWorkspaceCatalogRepository()
    failing_repository = FailingWorkspacePresetRepository(repository, SECOND_PRESET_KEY)
    unit_of_work = FakeUnitOfWork(repository)

    with pytest.raises(RuntimeError, match="workspace preset persistence failed"):
        RegisterWorkspacePresets(
            _provider(
                (
                    (FIRST_PRESET_KEY, first_definition),
                    (SECOND_PRESET_KEY, second_definition),
                )
            ),
            failing_repository,
            unit_of_work,
        ).execute()

    assert repository.definitions == {}
    assert repository.definition_ids_by_preset_key == {}
    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1
