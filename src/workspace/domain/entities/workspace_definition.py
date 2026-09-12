from uuid import UUID

from .workspace_component import WorkspaceComponent


class WorkspaceDefinition:
    """Workspaceの実行環境構成を識別する不変なDefinition。"""

    def __init__(
        self,
        *,
        definition_id: UUID,
        components: tuple[WorkspaceComponent, ...],
    ) -> None:
        self._definition_id = self._validate_definition_id(definition_id)
        self._components = self._validate_components(components)

    @property
    def definition_id(self) -> UUID:
        """WorkspaceDefinitionの識別子を返す。"""
        return self._definition_id

    @property
    def components(self) -> tuple[WorkspaceComponent, ...]:
        """WorkspaceDefinitionを構成するComponent列を返す。"""
        return self._components

    @staticmethod
    def _validate_definition_id(value: object) -> UUID:
        if not isinstance(value, UUID):
            raise TypeError("workspace definition id must be a UUID")

        return value

    @staticmethod
    def _validate_components(value: object) -> tuple[WorkspaceComponent, ...]:
        if not isinstance(value, tuple):
            raise TypeError("workspace definition components must be a tuple")
        if len(value) == 0:
            raise ValueError("workspace definition must contain at least one component")

        component_keys: set[str] = set()
        for component in value:
            if not isinstance(component, WorkspaceComponent):
                raise TypeError("workspace definition components must be WorkspaceComponent values")
            if component.component_key in component_keys:
                raise ValueError("workspace definition component keys must be unique")
            component_keys.add(component.component_key)

        return value
