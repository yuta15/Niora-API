import pytest

from src.workspace.domain.entities import TerminalExecAccessPoint


def test_terminal_exec_access_point_success_exposes_command() -> None:
    """TerminalExecAccessPointの接続コマンドを参照できることを確認する。"""
    command = ("/bin/bash",)
    access_point = TerminalExecAccessPoint(command)

    assert access_point.command == command


def test_terminal_exec_access_point_failure_rejects_command_assignment() -> None:
    """生成済みのTerminalExecAccessPointのコマンドを変更できないことを確認する。"""
    access_point = TerminalExecAccessPoint(("/bin/bash",))

    with pytest.raises(AttributeError):
        access_point.command = ("/bin/sh",)  # type: ignore[misc]


@pytest.mark.parametrize(
    ("command", "expected_exception"),
    [
        (["/bin/bash"], TypeError),
        ((), ValueError),
        (("",), ValueError),
        (("/bin/bash\x00",), ValueError),
        ((object(),), TypeError),
    ],
)
def test_terminal_exec_access_point_failure_rejects_invalid_command(
    command: object,
    expected_exception: type[Exception],
) -> None:
    """argvとして成立しないTerminal exec commandを指定できないことを確認する。"""
    with pytest.raises(expected_exception):
        TerminalExecAccessPoint(command)  # type: ignore[arg-type]
