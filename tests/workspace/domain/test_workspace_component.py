import pytest

from src.workspace.domain.entities import TerminalExecAccessPoint, WorkspaceComponent

COMPONENT_KEY = "ubuntu"
IMAGE = "ubuntu:latest"
STARTUP_COMMAND = ("sleep", "infinity")
TERMINAL_COMMAND = ("/bin/bash",)


def test_workspace_component_success_exposes_properties() -> None:
    """WorkspaceComponentの構成値を参照できることを確認する。"""
    terminal_exec = TerminalExecAccessPoint(TERMINAL_COMMAND)
    component = WorkspaceComponent(
        component_key=COMPONENT_KEY,
        image=IMAGE,
        startup_command=STARTUP_COMMAND,
        terminal_exec=terminal_exec,
    )

    assert component.component_key == COMPONENT_KEY
    assert component.image == IMAGE
    assert component.startup_command == STARTUP_COMMAND
    assert component.terminal_exec is terminal_exec


def test_workspace_component_success_allows_optional_properties_to_be_omitted() -> None:
    """WorkspaceComponentの任意プロパティを省略できることを確認する。"""
    component = WorkspaceComponent(component_key=COMPONENT_KEY, image=IMAGE)

    assert component.startup_command is None
    assert component.terminal_exec is None


@pytest.mark.parametrize(
    ("component_key", "image"),
    [
        (object(), "ubuntu:latest"),
        ("ubuntu", object()),
    ],
)
def test_workspace_component_failure_rejects_non_string_required_property(
    component_key: object,
    image: object,
) -> None:
    """必須プロパティへ文字列以外を指定できないことを確認する。"""
    with pytest.raises(TypeError):
        WorkspaceComponent(component_key=component_key, image=image)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("component_key", "image"),
    [
        ("", "ubuntu:latest"),
        ("ubuntu", ""),
    ],
)
def test_workspace_component_failure_rejects_empty_required_property(component_key: str, image: str) -> None:
    """必須プロパティへ空文字列を指定できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspaceComponent(component_key=component_key, image=image)


@pytest.mark.parametrize(
    ("startup_command", "expected_exception"),
    [
        ([], TypeError),
        ((), ValueError),
        (("",), ValueError),
        (("sleep\x00",), ValueError),
        ((object(),), TypeError),
    ],
)
def test_workspace_component_failure_rejects_invalid_startup_command(
    startup_command: object,
    expected_exception: type[Exception],
) -> None:
    """argvとして成立しないstartup commandを指定できないことを確認する。"""
    with pytest.raises(expected_exception):
        WorkspaceComponent(
            component_key=COMPONENT_KEY,
            image=IMAGE,
            startup_command=startup_command,  # type: ignore[arg-type]
        )


def test_workspace_component_failure_rejects_non_terminal_exec_access_point() -> None:
    """TerminalExecAccessPoint以外をTerminal接続点に指定できないことを確認する。"""
    with pytest.raises(TypeError):
        WorkspaceComponent(
            component_key=COMPONENT_KEY,
            image=IMAGE,
            terminal_exec=object(),  # type: ignore[arg-type]
        )


def test_workspace_component_failure_rejects_positional_arguments() -> None:
    """WorkspaceComponentのプロパティを位置引数で指定できないことを確認する。"""
    with pytest.raises(TypeError):
        WorkspaceComponent(COMPONENT_KEY, IMAGE)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("attribute_name", "new_value"),
    [
        ("component_key", "database"),
        ("image", "alpine:latest"),
        ("startup_command", ("/bin/sh",)),
        ("terminal_exec", TerminalExecAccessPoint(("/bin/sh",))),
    ],
)
def test_workspace_component_failure_rejects_property_assignment(attribute_name: str, new_value: object) -> None:
    """生成済みのWorkspaceComponentの公開プロパティを変更できないことを確認する。"""
    component = WorkspaceComponent(component_key=COMPONENT_KEY, image=IMAGE)

    with pytest.raises(AttributeError):
        setattr(component, attribute_name, new_value)
