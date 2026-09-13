from .terminal_exec_access_point import TerminalExecAccessPoint


class WorkspaceComponent:
    """WorkspaceDefinitionを構成するComponent。"""

    def __init__(
        self,
        *,
        component_key: str,
        image: str,
        startup_command: tuple[str, ...] | None = None,
        terminal_exec: TerminalExecAccessPoint | None = None,
    ) -> None:
        self._component_key = self._validate_required_string(component_key, "component key")
        self._image = self._validate_required_string(image, "component image")
        self._startup_command = self._validate_startup_command(startup_command)
        self._terminal_exec = self._validate_terminal_exec(terminal_exec)

    @property
    def component_key(self) -> str:
        """Componentの識別子を返す。"""
        return self._component_key

    @property
    def image(self) -> str:
        """Imageの識別情報を返す。"""
        return self._image

    @property
    def startup_command(self) -> tuple[str, ...] | None:
        """Componentの起動コマンドを返す。"""
        return self._startup_command

    @property
    def terminal_exec(self) -> TerminalExecAccessPoint | None:
        """ComponentのTerminal exec接続点を返す。"""
        return self._terminal_exec

    @staticmethod
    def _validate_required_string(value: object, name: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if value == "":
            raise ValueError(f"{name} must not be empty")

        return value

    @staticmethod
    def _validate_startup_command(value: object) -> tuple[str, ...] | None:
        if value is None:
            return None
        if not isinstance(value, tuple):
            raise TypeError("startup command must be a tuple")
        if len(value) == 0:
            raise ValueError("startup command must contain at least one argument")

        for index, argument in enumerate(value):
            if not isinstance(argument, str):
                raise TypeError("startup command arguments must be strings")
            if "\x00" in argument:
                raise ValueError("startup command arguments must not contain NUL")
            if index == 0 and argument == "":
                raise ValueError("startup command executable must not be empty")

        return value

    @staticmethod
    def _validate_terminal_exec(value: object) -> TerminalExecAccessPoint | None:
        if value is not None and not isinstance(value, TerminalExecAccessPoint):
            raise TypeError("terminal exec must be a TerminalExecAccessPoint or None")

        return value
