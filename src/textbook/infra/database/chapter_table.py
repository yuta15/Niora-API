from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database import Base


class ChapterTable(Base):
    """Chapterを永続化するTable Model。"""

    __tablename__ = "chapter"
    __table_args__ = (
        CheckConstraint("title <> ''", name="title_not_empty"),
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("textbook_id", "position", name="uq_chapter_textbook_id_position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    textbook_id: Mapped[UUID] = mapped_column(ForeignKey("textbook.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(length=128))
    position: Mapped[int] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    workspace_preset_key: Mapped[str | None] = mapped_column(String(length=128), nullable=True)
