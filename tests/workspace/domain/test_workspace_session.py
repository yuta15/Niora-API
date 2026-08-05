from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from src.workspace.domain.entities import WorkspacePresetKey, WorkspaceSession

WORKSPACE_SESSION_ID = UUID("b578c2b7-d5c2-4275-97be-a89665729719")
OTHER_WORKSPACE_SESSION_ID = UUID("a3239992-e19a-49bc-87c7-31ad9d502c69")
PRESET_KEY = WorkspacePresetKey("ws-ubuntu-24_04")
OTHER_PRESET_KEY = WorkspacePresetKey("ws-ubuntu-26_04")
EXPIRES_AT = datetime(2026, 8, 2, 15, 0, tzinfo=UTC)


def _workspace_session() -> WorkspaceSession:
    return WorkspaceSession(
        id=WORKSPACE_SESSION_ID,
        preset_key=PRESET_KEY,
        expires_at=EXPIRES_AT,
    )


def test_init_success_exposes_workspace_session_properties() -> None:
    """WorkspaceSessionの識別子、プリセットキー、有効期限を参照できることを確認する。"""
    workspace_session = _workspace_session()

    assert workspace_session.id == WORKSPACE_SESSION_ID
    assert workspace_session.preset_key == PRESET_KEY
    assert workspace_session.expires_at == EXPIRES_AT


@pytest.mark.parametrize("argument_name", ["id", "preset_key", "expires_at"])
def test_init_failure_rejects_invalid_argument_type(argument_name: str) -> None:
    """WorkspaceSessionを所定の型以外から生成できないことを確認する。"""
    arguments: dict[str, object] = {
        "id": WORKSPACE_SESSION_ID,
        "preset_key": PRESET_KEY,
        "expires_at": EXPIRES_AT,
    }
    arguments[argument_name] = object()

    with pytest.raises(TypeError):
        WorkspaceSession(**arguments)  # type: ignore[arg-type]


def test_init_failure_rejects_expiration_without_timezone() -> None:
    """タイムゾーンのない有効期限からWorkspaceSessionを生成できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspaceSession(
            id=WORKSPACE_SESSION_ID,
            preset_key=PRESET_KEY,
            expires_at=datetime(2026, 8, 2, 15, 0),
        )


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (EXPIRES_AT - timedelta(microseconds=1), False),
        (EXPIRES_AT, True),
        (EXPIRES_AT + timedelta(microseconds=1), True),
    ],
)
def test_is_expired_success_returns_expiration_at_specified_time(now: datetime, expected: bool) -> None:
    """有効期限の直前は利用可能で、有効期限以降は期限切れになることを確認する。"""
    assert _workspace_session().is_expired(now) is expected


def test_is_expired_failure_rejects_time_without_timezone() -> None:
    """タイムゾーンのない現在時刻では期限切れを判定できないことを確認する。"""
    with pytest.raises(ValueError):
        _workspace_session().is_expired(datetime(2026, 8, 2, 15, 0))


def test_is_expired_failure_rejects_non_datetime_value() -> None:
    """日時以外では期限切れを判定できないことを確認する。"""
    with pytest.raises(TypeError):
        _workspace_session().is_expired(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("attribute_name", "new_value"),
    [
        ("id", OTHER_WORKSPACE_SESSION_ID),
        ("preset_key", OTHER_PRESET_KEY),
        ("expires_at", EXPIRES_AT + timedelta(hours=1)),
    ],
)
def test_property_assignment_failure_is_rejected(attribute_name: str, new_value: object) -> None:
    """WorkspaceSessionの公開プロパティを直接変更できないことを確認する。"""
    workspace_session = _workspace_session()

    with pytest.raises(AttributeError):
        setattr(workspace_session, attribute_name, new_value)
