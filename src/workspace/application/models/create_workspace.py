from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateWorkspaceInput:
    """Workspaceの作成に必要な入力。"""

    textbook_id: UUID
    chapter_id: UUID


@dataclass(frozen=True)
class CreateWorkspaceOutput:
    """作成要求を完了したWorkspaceSessionの情報。"""

    id: UUID
    expires_at: datetime
