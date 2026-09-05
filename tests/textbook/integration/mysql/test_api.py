from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.textbook.infra.database import ChapterTable, TextbookTable

TEXTBOOK_ID = UUID("30000000-0000-0000-0000-000000000001")
OTHER_TEXTBOOK_ID = UUID("30000000-0000-0000-0000-000000000002")
FIRST_CHAPTER_ID = UUID("40000000-0000-0000-0000-000000000001")
SECOND_CHAPTER_ID = UUID("40000000-0000-0000-0000-000000000002")
OTHER_CHAPTER_ID = UUID("40000000-0000-0000-0000-000000000003")


@pytest.fixture
def api_catalog(mysql_session: Session) -> None:
    """APIの正常系とNot Found系を分離して検証するCatalogを投入する。"""
    mysql_session.add_all(
        [
            TextbookTable(id=TEXTBOOK_ID, title="Python基礎"),
            TextbookTable(id=OTHER_TEXTBOOK_ID, title="Python応用"),
        ]
    )
    mysql_session.flush()
    mysql_session.add_all(
        [
            ChapterTable(
                id=SECOND_CHAPTER_ID,
                textbook_id=TEXTBOOK_ID,
                title="第2章",
                position=1,
                content="second",
                workspace_preset_key=None,
            ),
            ChapterTable(
                id=FIRST_CHAPTER_ID,
                textbook_id=TEXTBOOK_ID,
                title="第1章",
                position=0,
                content="first",
                workspace_preset_key="python-basic",
            ),
            ChapterTable(
                id=OTHER_CHAPTER_ID,
                textbook_id=OTHER_TEXTBOOK_ID,
                title="別の章",
                position=0,
                content="other",
                workspace_preset_key=None,
            ),
        ]
    )
    mysql_session.commit()


@pytest.mark.integration
def test_api_success_returns_catalog_and_workspace_preset_values(
    mysql_api_client: TestClient,
    api_catalog: None,
) -> None:
    """実MySQLからAPIまでを通した一覧、教科書詳細、章詳細の契約を確認する。"""
    list_response = mysql_api_client.get("/v1/textbooks")
    textbook_response = mysql_api_client.get(f"/v1/textbooks/{TEXTBOOK_ID}")
    chapter_response = mysql_api_client.get(f"/v1/textbooks/{TEXTBOOK_ID}/chapters/{FIRST_CHAPTER_ID}")

    assert list_response.status_code == 200
    assert {(textbook["id"], textbook["title"]) for textbook in list_response.json()["textbooks"]} == {
        (str(TEXTBOOK_ID), "Python基礎"),
        (str(OTHER_TEXTBOOK_ID), "Python応用"),
    }
    assert textbook_response.status_code == 200
    assert [chapter["position"] for chapter in textbook_response.json()["chapters"]] == [0, 1]
    assert chapter_response.status_code == 200
    assert chapter_response.json() == {
        "id": str(FIRST_CHAPTER_ID),
        "title": "第1章",
        "content": "first",
        "workspace_preset_key": "python-basic",
    }

    nullable_chapter_response = mysql_api_client.get(f"/v1/textbooks/{TEXTBOOK_ID}/chapters/{SECOND_CHAPTER_ID}")
    assert nullable_chapter_response.status_code == 200
    assert nullable_chapter_response.json()["workspace_preset_key"] is None


@pytest.mark.integration
@pytest.mark.parametrize(
    "path",
    [
        f"/v1/textbooks/{TEXTBOOK_ID}/chapters/{UUID('40000000-0000-0000-0000-000000000099')}",
        f"/v1/textbooks/{UUID('30000000-0000-0000-0000-000000000099')}/chapters/{FIRST_CHAPTER_ID}",
        f"/v1/textbooks/{OTHER_TEXTBOOK_ID}/chapters/{FIRST_CHAPTER_ID}",
    ],
)
def test_api_failure_returns_chapter_not_found_for_missing_or_mismatched_chapter(
    mysql_api_client: TestClient,
    api_catalog: None,
    path: str,
) -> None:
    """章不存在または教科書所属が一致しない場合に既存の404契約を返すことを確認する。"""
    response = mysql_api_client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == "Chapter not found"


@pytest.mark.integration
def test_api_failure_returns_textbook_not_found_for_missing_textbook(
    mysql_api_client: TestClient,
    api_catalog: None,
) -> None:
    """教科書が存在しない場合に既存の404契約を返すことを確認する。"""
    response = mysql_api_client.get("/v1/textbooks/30000000-0000-0000-0000-000000000099")

    assert response.status_code == 404
    assert response.json()["detail"] == "Textbook not found"
