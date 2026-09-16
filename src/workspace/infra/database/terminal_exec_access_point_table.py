from uuid import UUID

from sqlalchemy import JSON, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database import Base


class TerminalAccessPointTable(Base):
    __tablename__ = "terminal_access_point_table"
    __table_args__ = (
        ForeignKeyConstraint(
            ["definition_id", "component_key"],
            [
                "workspace_component.definition_id",
                "workspace_component.component_key",
            ],
            ondelete="CASCADE",
        ),
    )

    definition_id: Mapped[UUID] = mapped_column(primary_key=True)
    component_key: Mapped[str] = mapped_column(String(length=128), primary_key=True)
    command: Mapped[list[str]] = mapped_column(JSON())
