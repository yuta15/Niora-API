from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.workspace.domain import TerminalExecAccessPoint, WorkspacePresetKey, WorkspaceSession
from src.workspace.infra.database import (
    PresetWorkspaceDefinitionMappingTable,
    SqlAlchemyWorkspaceDefinitionIdResolver,
    SqlAlchemyWorkspaceDefinitionRepository,
    SqlAlchemyWorkspaceSessionRepository,
    TerminalAccessPointTable,
    WorkspaceComponentTable,
    WorkspaceDefinitionTable,
    WorkspaceSessionTable,
)


@pytest.mark.integration
def test_resolve_success_returns_definition_id_for_preset_key(mysql_session: Session) -> None:
    """Preset Keyに対応するDefinition IDをMySQLから解決できることを確認する。"""
    definition_id = UUID("10000000-0000-0000-0000-000000000001")
    preset_key = "python-basic"
    mysql_session.add(WorkspaceDefinitionTable(id=definition_id))
    mysql_session.flush()
    mysql_session.add(PresetWorkspaceDefinitionMappingTable(preset_key=preset_key, definition_id=definition_id))
    mysql_session.commit()
    resolver = SqlAlchemyWorkspaceDefinitionIdResolver(mysql_session)

    resolved_id = resolver.resolve(WorkspacePresetKey(preset_key))

    assert resolved_id == definition_id


@pytest.mark.integration
def test_resolve_success_returns_none_when_preset_key_is_missing(mysql_session: Session) -> None:
    """対応するMappingがないPreset Keyの解決結果がNoneであることを確認する。"""
    resolver = SqlAlchemyWorkspaceDefinitionIdResolver(mysql_session)

    resolved_id = resolver.resolve(WorkspacePresetKey("missing-preset"))

    assert resolved_id is None


@pytest.mark.integration
def test_get_success_restores_components_in_order_and_optional_values(mysql_session: Session) -> None:
    """DefinitionのComponent順序、任意の起動Command、Terminalを復元できることを確認する。"""
    definition_id = UUID("20000000-0000-0000-0000-000000000001")
    mysql_session.add(WorkspaceDefinitionTable(id=definition_id))
    mysql_session.flush()
    mysql_session.add_all(
        [
            WorkspaceComponentTable(
                definition_id=definition_id,
                component_key="terminal",
                image="python:3.13",
                position=1,
                startup_command=["python", "-m", "app"],
            ),
            WorkspaceComponentTable(
                definition_id=definition_id,
                component_key="workspace",
                image="ubuntu:24.04",
                position=0,
                startup_command=None,
            ),
        ]
    )
    mysql_session.flush()
    mysql_session.add(
        TerminalAccessPointTable(
            definition_id=definition_id,
            component_key="terminal",
            command=["/bin/bash"],
        )
    )
    mysql_session.commit()
    repository = SqlAlchemyWorkspaceDefinitionRepository(mysql_session)

    definition = repository.get(definition_id)

    assert definition is not None
    assert definition.definition_id == definition_id
    assert [component.component_key for component in definition.components] == ["workspace", "terminal"]
    assert definition.components[0].startup_command is None
    assert definition.components[0].terminal_exec is None
    assert definition.components[1].startup_command == ("python", "-m", "app")
    assert isinstance(definition.components[1].terminal_exec, TerminalExecAccessPoint)
    assert definition.components[1].terminal_exec.command == ("/bin/bash",)


@pytest.mark.integration
def test_get_success_returns_none_when_definition_is_missing(mysql_session: Session) -> None:
    """DefinitionのRoot行が存在しない場合にNoneを返すことを確認する。"""
    repository = SqlAlchemyWorkspaceDefinitionRepository(mysql_session)

    definition = repository.get(UUID("20000000-0000-0000-0000-000000000099"))

    assert definition is None


@pytest.mark.integration
def test_get_failure_rejects_definition_without_components(mysql_session: Session) -> None:
    """ComponentのないDefinitionを取得するとDomain制約違反になることを確認する。"""
    definition_id = UUID("20000000-0000-0000-0000-000000000002")
    mysql_session.add(WorkspaceDefinitionTable(id=definition_id))
    mysql_session.commit()
    repository = SqlAlchemyWorkspaceDefinitionRepository(mysql_session)

    with pytest.raises(ValueError, match="workspace definition must contain at least one component"):
        repository.get(definition_id)


@pytest.mark.integration
def test_get_failure_rejects_string_startup_command(mysql_session: Session) -> None:
    """startup_commandがJSON文字列の場合に型エラーを送出することを確認する。"""
    definition_id = UUID("20000000-0000-0000-0000-000000000003")
    mysql_session.add(WorkspaceDefinitionTable(id=definition_id))
    mysql_session.flush()
    mysql_session.add(
        WorkspaceComponentTable(
            definition_id=definition_id,
            component_key="workspace",
            image="ubuntu:24.04",
            position=0,
            startup_command="python -m app",
        )
    )
    mysql_session.commit()
    repository = SqlAlchemyWorkspaceDefinitionRepository(mysql_session)

    with pytest.raises(TypeError, match="startup command must be a list of strings"):
        repository.get(definition_id)


@pytest.mark.integration
def test_get_failure_rejects_null_terminal_command(mysql_session: Session) -> None:
    """Terminal行のcommandがJSON nullの場合に型エラーを送出することを確認する。"""
    definition_id = UUID("20000000-0000-0000-0000-000000000004")
    mysql_session.add(WorkspaceDefinitionTable(id=definition_id))
    mysql_session.flush()
    mysql_session.add(
        WorkspaceComponentTable(
            definition_id=definition_id,
            component_key="terminal",
            image="python:3.13",
            position=0,
            startup_command=None,
        )
    )
    mysql_session.flush()
    mysql_session.add(
        TerminalAccessPointTable(
            definition_id=definition_id,
            component_key="terminal",
            command=None,
        )
    )
    mysql_session.commit()
    repository = SqlAlchemyWorkspaceDefinitionRepository(mysql_session)

    with pytest.raises(TypeError, match="terminal exec command must be a list of strings"):
        repository.get(definition_id)


@pytest.mark.integration
def test_add_success_stores_session_with_utc_datetime(mysql_session: Session) -> None:
    """WorkspaceSessionの期限日時をUTCへ変換して保存することを確認する。"""
    definition_id = UUID("30000000-0000-0000-0000-000000000001")
    session_id = UUID("40000000-0000-0000-0000-000000000001")
    expires_at = datetime(2030, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=9)))
    expected_utc = datetime(2030, 1, 1, 3, 0, tzinfo=UTC)
    mysql_session.add(WorkspaceDefinitionTable(id=definition_id))
    mysql_session.commit()
    repository = SqlAlchemyWorkspaceSessionRepository(mysql_session)

    repository.add(WorkspaceSession(session_id, definition_id, expires_at))
    mysql_session.commit()
    stored_table = mysql_session.get(WorkspaceSessionTable, session_id)

    assert stored_table is not None
    assert stored_table.expires_at == expected_utc.replace(tzinfo=None)
    assert stored_table.expires_at.tzinfo is None


@pytest.mark.integration
def test_get_success_returns_session_with_utc_aware_datetime(mysql_session: Session) -> None:
    """MySQLのnaiveな期限日時をUTC awareへ変換してSessionを復元することを確認する。"""
    definition_id = UUID("30000000-0000-0000-0000-000000000002")
    session_id = UUID("40000000-0000-0000-0000-000000000002")
    expires_at = datetime(2030, 1, 1, 3, 0)
    mysql_session.add(WorkspaceDefinitionTable(id=definition_id))
    mysql_session.flush()
    mysql_session.add(WorkspaceSessionTable(id=session_id, definition_id=definition_id, expires_at=expires_at))
    mysql_session.commit()
    repository = SqlAlchemyWorkspaceSessionRepository(mysql_session)

    retrieved = repository.get(session_id)

    assert retrieved is not None
    assert retrieved.id == session_id
    assert retrieved.definition_id == definition_id
    assert retrieved.expires_at == expires_at.replace(tzinfo=UTC)
    assert retrieved.expires_at.utcoffset() == timedelta(0)


@pytest.mark.integration
def test_delete_success_removes_session(mysql_session: Session) -> None:
    """指定したWorkspaceSessionを削除することを確認する。"""
    definition_id = UUID("30000000-0000-0000-0000-000000000003")
    session_id = UUID("40000000-0000-0000-0000-000000000003")
    mysql_session.add(WorkspaceDefinitionTable(id=definition_id))
    mysql_session.flush()
    mysql_session.add(
        WorkspaceSessionTable(
            id=session_id,
            definition_id=definition_id,
            expires_at=datetime(2030, 1, 1, 3, 0),
        )
    )
    mysql_session.commit()
    repository = SqlAlchemyWorkspaceSessionRepository(mysql_session)

    repository.delete(session_id)
    mysql_session.commit()

    assert mysql_session.get(WorkspaceSessionTable, session_id) is None


@pytest.mark.integration
def test_delete_success_treats_missing_session_as_noop(mysql_session: Session) -> None:
    """存在しないWorkspaceSessionの削除要求が例外を発生させないことを確認する。"""
    repository = SqlAlchemyWorkspaceSessionRepository(mysql_session)

    repository.delete(UUID("40000000-0000-0000-0000-000000000099"))
