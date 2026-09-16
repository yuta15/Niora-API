from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database import Base


class PresetWorkspaceDefinitionMappingTable(Base):
    __tablename__ = "preset_workspace_definition_mapping"
    __table_args__ = (
        UniqueConstraint(
            "preset_key",
            "definition_id",
            name="uq_preset_key_definition_id",
        ),
    )

    preset_key: Mapped[str] = mapped_column(String(length=128), primary_key=True)
    definition_id: Mapped[UUID] = mapped_column(ForeignKey("workspace_definition.id", ondelete="CASCADE"))
