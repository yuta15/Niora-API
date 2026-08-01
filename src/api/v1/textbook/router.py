from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import provide_get_chapter, provide_get_textbook, provide_list_textbooks
from src.api.v1.textbook.schemas import GetChapterResponse, GetTextbookResponse, ListTextbooksResponse
from src.textbook.application.models import GetChapterInput, GetTextbookInput
from src.textbook.application.usecases import GetChapter, GetTextbook, ListTextbooks

router = APIRouter(tags=["textbooks"])


@router.get(
    "/textbooks",
    response_model=ListTextbooksResponse,
    status_code=status.HTTP_200_OK,
)
def list_textbooks(
    use_case: Annotated[ListTextbooks, Depends(provide_list_textbooks)],
) -> ListTextbooksResponse:
    """教科書の一覧を返す。"""
    output = use_case.execute()
    return ListTextbooksResponse.from_output(output)


@router.get(
    "/textbooks/{textbook_id}",
    response_model=GetTextbookResponse,
    status_code=status.HTTP_200_OK,
)
def get_textbook(
    textbook_id: UUID,
    use_case: Annotated[GetTextbook, Depends(provide_get_textbook)],
) -> GetTextbookResponse:
    """指定された教科書を返す。"""
    output = use_case.execute(GetTextbookInput(textbook_id=textbook_id))
    if output is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Textbook not found",
        )

    return GetTextbookResponse.from_output(output)


@router.get(
    "/textbooks/{textbook_id}/chapters/{chapter_id}",
    response_model=GetChapterResponse,
    status_code=status.HTTP_200_OK,
)
def get_chapter(
    textbook_id: UUID,
    chapter_id: UUID,
    use_case: Annotated[GetChapter, Depends(provide_get_chapter)],
) -> GetChapterResponse:
    """指定された章を返す。"""
    output = use_case.execute(
        GetChapterInput(
            textbook_id=textbook_id,
            chapter_id=chapter_id,
        )
    )
    if output is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found",
        )

    return GetChapterResponse.from_output(output)
