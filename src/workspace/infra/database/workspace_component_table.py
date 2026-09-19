from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database import Base


class WorkspaceComponentTable(Base):
    __tablename__ = "workspace_component"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("definition_id", "position", name="uq_definition_id_position"),
    )

    definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace_definition.id", ondelete="CASCADE"), primary_key=True
    )
    component_key: Mapped[str] = mapped_column(String(length=128, collation="utf8mb4_0900_bin"), primary_key=True)
    image: Mapped[str] = mapped_column(String(length=512))
    position: Mapped[int] = mapped_column()
    startup_command: Mapped[list[str]] = mapped_column(JSON, nullable=True)
