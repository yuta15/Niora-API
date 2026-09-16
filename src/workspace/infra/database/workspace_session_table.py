from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database import Base


class WorkspaceSessionTable(Base):
    """Workspae Sessionを永続化するTable Model."""

    __tablename__ = "workspace_session"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    definition_id: Mapped[UUID] = mapped_column(ForeignKey("workspace_definition.id", ondelete="RESTRICT"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
