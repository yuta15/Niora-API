from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.textbook.infra.database import SqlAlchemyTextbookRepository, TextbookTable


@pytest.mark.integration
def test_list_success_returns_all_textbooks(mysql_session: Session) -> None:
    """Textbook一覧が保存されたすべてのTextbookをDomain Entityとして返すことを確認する。"""
    mysql_session.add_all(
        [
            TextbookTable(id=UUID("00000000-0000-0000-0000-000000000002"), title="Python応用"),
            TextbookTable(id=UUID("00000000-0000-0000-0000-000000000001"), title="Python基礎"),
        ]
    )
    mysql_session.commit()
    repository = SqlAlchemyTextbookRepository(mysql_session)

    textbooks = repository.list()

    assert {(textbook.id, textbook.title.value) for textbook in textbooks} == {
        (UUID("00000000-0000-0000-0000-000000000001"), "Python基礎"),
        (UUID("00000000-0000-0000-0000-000000000002"), "Python応用"),
    }


@pytest.mark.integration
def test_get_success_returns_textbook(mysql_session: Session) -> None:
    """Textbookを識別子で取得してDomain Entityへ変換できることを確認する。"""
    textbook_id = UUID("00000000-0000-0000-0000-000000000001")
    mysql_session.add(TextbookTable(id=textbook_id, title="Python基礎"))
    mysql_session.commit()
    repository = SqlAlchemyTextbookRepository(mysql_session)

    textbook = repository.get(textbook_id)

    assert textbook is not None
    assert textbook.id == textbook_id
    assert textbook.title.value == "Python基礎"


@pytest.mark.integration
def test_get_success_returns_none_when_textbook_does_not_exist(mysql_session: Session) -> None:
    """指定した識別子のTextbookが存在しない場合にNoneを返すことを確認する。"""
    repository = SqlAlchemyTextbookRepository(mysql_session)

    textbook = repository.get(UUID("00000000-0000-0000-0000-000000000099"))

    assert textbook is None
