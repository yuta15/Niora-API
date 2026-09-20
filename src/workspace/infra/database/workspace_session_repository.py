from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from src.workspace.application.ports import WorkspaceSessionRepository
from src.workspace.domain import WorkspaceSession

from .workspace_session_table import WorkspaceSessionTable


class SqlAlchemyWorkspaceSessionRepository(WorkspaceSessionRepository):
    """SQLAlchemyを使用してWorkspaceSessionを永続化するRepository。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, id: UUID) -> WorkspaceSession | None:
        """指定した識別子のWorkspaceSessionを返す。"""
        table = self._session.get(WorkspaceSessionTable, id)
        if table is None:
            return None

        return WorkspaceSession(
            id=table.id,
            definition_id=table.definition_id,
            expires_at=self._as_utc_aware(table.expires_at),
        )

    def add(self, session: WorkspaceSession) -> None:
        """WorkspaceSessionをSessionへ追加する。"""
        self._session.add(
            WorkspaceSessionTable(
                id=session.id,
                definition_id=session.definition_id,
                expires_at=self._as_utc_naive(session.expires_at),
            )
        )

    def delete(self, id: UUID) -> None:
        """WorkspaceSessionが存在する場合にSessionへ削除を追加する。"""
        table = self._session.get(WorkspaceSessionTable, id)
        if table is not None:
            self._session.delete(table)

    @staticmethod
    def _as_utc_naive(value: datetime) -> datetime:
        return value.astimezone(UTC).replace(tzinfo=None)

    @staticmethod
    def _as_utc_aware(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
