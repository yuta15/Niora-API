import re
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspacePresetKey:
    """Nioraが提供するWorkspaceのプリセットを識別する不変のキー。"""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError("workspace preset key must be a string")

        MIN_LENGTH = 1
        MAX_LENGTH = 128
        if not MIN_LENGTH <= len(self.value) <= MAX_LENGTH:
            raise ValueError(f"workspace preset key must contain {MIN_LENGTH} to {MAX_LENGTH} characters")
        if re.fullmatch(r"[A-Za-z0-9_-]+", self.value) is None:
            raise ValueError("workspace preset key must contain only ASCII letters, numbers, hyphens, and underscores")
