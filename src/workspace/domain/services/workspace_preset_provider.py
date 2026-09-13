from collections.abc import Mapping
from uuid import UUID

from ..entities import WorkspaceDefinition, WorkspacePreset, WorkspacePresetKey


class WorkspacePresetProvider:
    """分離して定義したPreset keyとWorkspaceDefinitionを対応付けて提供する。"""

    def __init__(
        self,
        *,
        preset_keys: tuple[WorkspacePresetKey, ...],
        definitions: tuple[WorkspaceDefinition, ...],
        definition_ids_by_preset_key: Mapping[WorkspacePresetKey, UUID],
    ) -> None:
        validated_preset_keys = self._validate_preset_keys(preset_keys)
        definitions_by_id = self._index_definitions(definitions)
        validated_associations = self._validate_associations(
            definition_ids_by_preset_key,
            preset_keys=validated_preset_keys,
            definition_ids=frozenset(definitions_by_id),
        )

        self._preset_keys = validated_preset_keys
        self._presets_by_key = {
            preset_key: WorkspacePreset(
                preset_key=preset_key,
                definition=definitions_by_id[validated_associations[preset_key]],
            )
            for preset_key in validated_preset_keys
        }

    def list_preset_keys(self) -> tuple[WorkspacePresetKey, ...]:
        """提供しているPreset keyを定義順に返す。"""
        return self._preset_keys

    def list_presets(self) -> tuple[WorkspacePreset, ...]:
        """提供しているWorkspacePresetを定義順に返す。"""
        return tuple(self._presets_by_key[preset_key] for preset_key in self._preset_keys)

    def get(self, preset_key: WorkspacePresetKey) -> WorkspacePreset | None:
        """Preset keyに対応するWorkspacePresetを返す。"""
        if not isinstance(preset_key, WorkspacePresetKey):
            raise TypeError("workspace preset key must be a WorkspacePresetKey")

        return self._presets_by_key.get(preset_key)

    @staticmethod
    def _validate_preset_keys(value: object) -> tuple[WorkspacePresetKey, ...]:
        if not isinstance(value, tuple):
            raise TypeError("workspace preset keys must be a tuple")

        preset_keys: set[WorkspacePresetKey] = set()
        for preset_key in value:
            if not isinstance(preset_key, WorkspacePresetKey):
                raise TypeError("workspace preset keys must contain only WorkspacePresetKey values")
            if preset_key in preset_keys:
                raise ValueError("workspace preset keys must be unique")
            preset_keys.add(preset_key)

        return value

    @staticmethod
    def _index_definitions(value: object) -> dict[UUID, WorkspaceDefinition]:
        if not isinstance(value, tuple):
            raise TypeError("workspace preset definitions must be a tuple")

        definitions_by_id: dict[UUID, WorkspaceDefinition] = {}
        for definition in value:
            if not isinstance(definition, WorkspaceDefinition):
                raise TypeError("workspace preset definitions must contain only WorkspaceDefinition values")
            if definition.definition_id in definitions_by_id:
                raise ValueError("workspace preset definition ids must be unique")
            definitions_by_id[definition.definition_id] = definition

        return definitions_by_id

    @staticmethod
    def _validate_associations(
        value: object,
        *,
        preset_keys: tuple[WorkspacePresetKey, ...],
        definition_ids: frozenset[UUID],
    ) -> dict[WorkspacePresetKey, UUID]:
        if not isinstance(value, Mapping):
            raise TypeError("workspace preset associations must be a mapping")

        associations: dict[WorkspacePresetKey, UUID] = {}
        for preset_key, definition_id in value.items():
            if not isinstance(preset_key, WorkspacePresetKey):
                raise TypeError("workspace preset association keys must be WorkspacePresetKey values")
            if not isinstance(definition_id, UUID):
                raise TypeError("workspace preset association values must be UUID values")
            associations[preset_key] = definition_id

        if frozenset(associations) != frozenset(preset_keys):
            raise ValueError("workspace preset associations must contain every preset key exactly once")

        associated_definition_ids = tuple(associations.values())
        if len(set(associated_definition_ids)) != len(associated_definition_ids):
            raise ValueError("workspace preset associations must use unique definition ids")
        if frozenset(associated_definition_ids) != definition_ids:
            raise ValueError("workspace preset associations must contain every definition exactly once")

        return associations
