from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database import Base


class PresetWorkspaceDefinitionMappingTable(Base):
    __tablename__ = "preset_workspace_definition_mapping"

    preset_key: Mapped[str] = mapped_column(String(length=512, collation="utf8mb4_0900_bin"), primary_key=True)
    definition_id: Mapped[UUID] = mapped_column(ForeignKey("workspace_definition.id", ondelete="CASCADE"), unique=True)
