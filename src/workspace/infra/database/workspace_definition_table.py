from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database import Base


class WorkspaceDefinitionTable(Base):
    __tablename__ = "workspace_definition"

    id: Mapped[UUID] = mapped_column(primary_key=True)
