class TerminalExecAccessPoint:
    """Componentに紐づくTerminal exec接続点。"""

    def __init__(self, command: tuple[str, ...]) -> None:
        self._command = self._validate_command(command)

    @property
    def command(self) -> tuple[str, ...]:
        """Terminal接続時に実行するコマンドを返す。"""
        return self._command

    @staticmethod
    def _validate_command(value: object) -> tuple[str, ...]:
        if not isinstance(value, tuple):
            raise TypeError("terminal exec command must be a tuple")
        if len(value) == 0:
            raise ValueError("terminal exec command must contain at least one argument")

        for index, argument in enumerate(value):
            if not isinstance(argument, str):
                raise TypeError("terminal exec command arguments must be strings")
            if "\x00" in argument:
                raise ValueError("terminal exec command arguments must not contain NUL")
            if index == 0 and argument == "":
                raise ValueError("terminal exec command executable must not be empty")

        return value
