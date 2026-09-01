from dataclasses import dataclass


@dataclass(frozen=True)
class TitleString:
    """前後の空白を除いた1文字以上128文字以下のタイトル。"""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError("title must be a string")

        normalized_value = self.value.strip()
        MAX_LENGTH = 128
        MIN_LENGTH = 1
        if len(normalized_value) < MIN_LENGTH or MAX_LENGTH < len(normalized_value):
            raise ValueError(f"title must be include {MIN_LENGTH} to {MAX_LENGTH} characters or fewer")

        object.__setattr__(self, "value", normalized_value)


@dataclass(frozen=True)
class ContentString:
    """空文字列を許容する章の本文。"""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError("value must be a string")


@dataclass(frozen=True)
class ChapterPosition:
    """教科書内における0始まりの章の位置。"""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise TypeError("chapter position must be an integer")
        if self.value < 0:
            raise ValueError("chapter position must be 0 or greater")
