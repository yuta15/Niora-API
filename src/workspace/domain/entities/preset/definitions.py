from uuid import UUID

from ..terminal_exec_access_point import TerminalExecAccessPoint
from ..workspace_component import WorkspaceComponent
from ..workspace_definition import WorkspaceDefinition

UBUNTU_24_04_WORKSPACE_DEFINITION = WorkspaceDefinition(
    definition_id=UUID("1f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5"),
    components=(
        WorkspaceComponent(
            component_key="main",
            image="ubuntu:24.04",
            startup_command=("sleep", "infinity"),
            terminal_exec=TerminalExecAccessPoint(("/bin/bash",)),
        ),
    ),
)

SYSTEM_WORKSPACE_DEFINITIONS = (UBUNTU_24_04_WORKSPACE_DEFINITION,)
