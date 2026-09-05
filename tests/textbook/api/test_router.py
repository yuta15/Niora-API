from collections.abc import Callable
from uuid import UUID

import pytest
from fastapi import HTTPException, status
from fastapi.routing import APIRoute
from pydantic import BaseModel
from pytest_mock import MockerFixture

from src.api.dependencies import provide_get_chapter, provide_get_textbook, provide_list_textbooks
from src.api.v1.textbook.router import get_chapter, get_textbook, list_textbooks, router
from src.api.v1.textbook.schemas import (
    ChapterSummaryResponse,
    GetChapterResponse,
    GetTextbookResponse,
    ListTextbooksResponse,
    TextbookSummaryResponse,
)
from src.textbook.application.models import (
    ChapterSummary,
    GetChapterInput,
    GetChapterOutput,
    GetTextbookOutput,
    ListTextbooksOutput,
    TextbookSummary,
)
from src.textbook.application.usecases import GetChapter, GetTextbook, ListTextbooks

TEXTBOOK_ID = UUID("72bc9284-a55d-4594-8ca4-654c5ca45e64")
CHAPTER_ID = UUID("ee3d85df-1a4d-4c0c-a1f1-762567592e04")


@pytest.mark.parametrize(
    ("path", "endpoint", "response_model", "dependency_provider"),
    [
        ("/textbooks", list_textbooks, ListTextbooksResponse, provide_list_textbooks),
        ("/textbooks/{textbook_id}", get_textbook, GetTextbookResponse, provide_get_textbook),
        (
            "/textbooks/{textbook_id}/chapters/{chapter_id}",
            get_chapter,
            GetChapterResponse,
            provide_get_chapter,
        ),
    ],
)
def test_router_success_declares_operation_contract(
    path: str,
    endpoint: Callable[..., object],
    response_model: type[BaseModel],
    dependency_provider: Callable[..., object],
) -> None:
    """公開経路が既存契約と指定されたUseCase providerを登録することを確認する。"""
    route = next(route for route in router.routes if isinstance(route, APIRoute) and route.path == path)

    assert route.methods == {"GET"}
    assert route.status_code == status.HTTP_200_OK
    assert route.response_model is response_model
    assert route.endpoint is endpoint
    assert [dependency.call for dependency in route.dependant.dependencies] == [dependency_provider]


def test_list_textbooks_success_converts_output_to_response_schema(mocker: MockerFixture) -> None:
    """教科書一覧のApplication出力が公開レスポンスへ変換されることを確認する。"""
    use_case = mocker.Mock(spec=ListTextbooks)
    use_case.execute.return_value = ListTextbooksOutput(
        textbooks=(TextbookSummary(id=TEXTBOOK_ID, title="Python入門"),),
    )

    response = list_textbooks(use_case)

    assert response == ListTextbooksResponse(
        textbooks=(TextbookSummaryResponse(id=TEXTBOOK_ID, title="Python入門"),),
    )


def test_get_textbook_success_converts_output_to_response_schema(mocker: MockerFixture) -> None:
    """教科書詳細のApplication出力が公開レスポンスへ変換されることを確認する。"""
    use_case = mocker.Mock(spec=GetTextbook)
    use_case.execute.return_value = GetTextbookOutput(
        id=TEXTBOOK_ID,
        title="Python入門",
        chapters=(ChapterSummary(id=CHAPTER_ID, title="基本構文", position=1),),
    )

    response = get_textbook(TEXTBOOK_ID, use_case)

    assert response == GetTextbookResponse(
        id=TEXTBOOK_ID,
        title="Python入門",
        chapters=(ChapterSummaryResponse(id=CHAPTER_ID, title="基本構文", position=1),),
    )


def test_get_textbook_failure_returns_not_found(mocker: MockerFixture) -> None:
    """存在しない教科書の取得が既存の404 detailを返すことを確認する。"""
    use_case = mocker.Mock(spec=GetTextbook)
    use_case.execute.return_value = None

    with pytest.raises(HTTPException) as exception_info:
        get_textbook(TEXTBOOK_ID, use_case)

    assert exception_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exception_info.value.detail == "Textbook not found"


def test_get_chapter_success_converts_output_to_response_schema(mocker: MockerFixture) -> None:
    """章詳細のApplication出力が公開レスポンスへ変換されることを確認する。"""
    use_case = mocker.Mock(spec=GetChapter)
    use_case.execute.return_value = GetChapterOutput(
        id=CHAPTER_ID,
        title="基本構文",
        content="print('Hello, world!')",
        workspace_preset_key=None,
    )

    response = get_chapter(TEXTBOOK_ID, CHAPTER_ID, use_case)

    assert response == GetChapterResponse(
        id=CHAPTER_ID,
        title="基本構文",
        content="print('Hello, world!')",
        workspace_preset_key=None,
    )
    use_case.execute.assert_called_once_with(
        GetChapterInput(
            textbook_id=TEXTBOOK_ID,
            chapter_id=CHAPTER_ID,
        )
    )


def test_get_chapter_failure_returns_not_found(mocker: MockerFixture) -> None:
    """存在しない章の取得が既存の404 detailを返すことを確認する。"""
    use_case = mocker.Mock(spec=GetChapter)
    use_case.execute.return_value = None

    with pytest.raises(HTTPException) as exception_info:
        get_chapter(TEXTBOOK_ID, CHAPTER_ID, use_case)

    assert exception_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exception_info.value.detail == "Chapter not found"
    use_case.execute.assert_called_once_with(
        GetChapterInput(
            textbook_id=TEXTBOOK_ID,
            chapter_id=CHAPTER_ID,
        )
    )
