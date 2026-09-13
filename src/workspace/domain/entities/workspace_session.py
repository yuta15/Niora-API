from datetime import datetime
from uuid import UUID


class WorkspaceSession:
    """起動してから終了するまでの期限付き学習環境。"""

    def __init__(
        self,
        id: UUID,
        definition_id: UUID,
        expires_at: datetime,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("workspace session id must be a UUID")
        if not isinstance(definition_id, UUID):
            raise TypeError("workspace definition id must be a UUID")
        self._validate_aware_datetime(expires_at, "workspace session expiration")

        self._id = id
        self._definition_id = definition_id
        self._expires_at = expires_at

    @property
    def id(self) -> UUID:
        """WorkspaceSessionの識別子を返す。"""
        return self._id

    @property
    def definition_id(self) -> UUID:
        """関連するWorkspaceDefinitionの識別子を返す。"""
        return self._definition_id

    @property
    def expires_at(self) -> datetime:
        """WorkspaceSessionの有効期限を返す。"""
        return self._expires_at

    def is_expired(self, now: datetime) -> bool:
        """指定した時刻にWorkspaceSessionが期限切れかを返す。"""
        self._validate_aware_datetime(now, "current time")
        return now >= self._expires_at

    @staticmethod
    def _validate_aware_datetime(value: object, name: str) -> None:
        if not isinstance(value, datetime):
            raise TypeError(f"{name} must be a datetime")
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must include timezone information")
