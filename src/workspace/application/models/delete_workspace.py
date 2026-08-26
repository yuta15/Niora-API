from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DeleteWorkspaceInput:
    """Workspaceの削除に必要な入力。"""

    workspace_session_id: UUID
