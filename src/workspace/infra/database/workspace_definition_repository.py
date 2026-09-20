from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.workspace.application.ports import WorkspaceDefinitionRepository
from src.workspace.domain import TerminalExecAccessPoint, WorkspaceComponent, WorkspaceDefinition

from .terminal_exec_access_point_table import TerminalAccessPointTable
from .workspace_component_table import WorkspaceComponentTable
from .workspace_definition_table import WorkspaceDefinitionTable


class SqlAlchemyWorkspaceDefinitionRepository(WorkspaceDefinitionRepository):
    """SQLAlchemyを使用してWorkspaceDefinitionを読み取るRepository。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, definition_id: UUID) -> WorkspaceDefinition | None:
        """指定した識別子のDefinitionを返す。"""
        statement = (
            select(WorkspaceComponentTable, TerminalAccessPointTable)
            .outerjoin(
                TerminalAccessPointTable,
                and_(
                    TerminalAccessPointTable.definition_id == WorkspaceComponentTable.definition_id,
                    TerminalAccessPointTable.component_key == WorkspaceComponentTable.component_key,
                ),
            )
            .where(WorkspaceComponentTable.definition_id == definition_id)
            .order_by(WorkspaceComponentTable.position.asc())
        )
        rows = self._session.execute(statement).all()
        if not rows:
            definition_table = self._session.get(WorkspaceDefinitionTable, definition_id)
            if definition_table is None:
                return None

        components = []
        for component_table, terminal_access_point_table in rows:
            terminal_exec = None
            if terminal_access_point_table is not None:
                terminal_command = self._command_as_tuple(
                    terminal_access_point_table.command,
                    "terminal exec command",
                )
                terminal_exec = TerminalExecAccessPoint(command=terminal_command)

            startup_command = None
            if component_table.startup_command is not None:
                startup_command = self._command_as_tuple(component_table.startup_command, "startup command")

            components.append(
                WorkspaceComponent(
                    component_key=component_table.component_key,
                    image=component_table.image,
                    startup_command=startup_command,
                    terminal_exec=terminal_exec,
                )
            )

        return WorkspaceDefinition(definition_id=definition_id, components=tuple(components))

    @staticmethod
    def _command_as_tuple(value: object, name: str) -> tuple[str, ...]:
        if not isinstance(value, list) or any(not isinstance(argument, str) for argument in value):
            raise TypeError(f"{name} must be a list of strings")

        return tuple(value)
