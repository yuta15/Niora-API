from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    """Applicationへ現在時刻を提供する。"""

    @abstractmethod
    def now(self) -> datetime:
        """タイムゾーン情報を含む現在時刻を返す。"""
