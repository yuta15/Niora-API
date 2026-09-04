from uuid import UUID

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database import Base


class TextbookTable(Base):
    """Textbookを永続化するTable Model。"""

    __tablename__ = "textbook"
    __table_args__ = (CheckConstraint("title <> ''", name="title_not_empty"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(length=128))
