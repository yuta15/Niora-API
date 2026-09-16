from abc import ABC, abstractmethod

from src.workspace.domain import WorkspacePreset


class WorkspacePresetRepository(ABC):
    """WorkspacePreset Catalogへの追記操作を定義する。"""

    @abstractmethod
    def register(self, preset: WorkspacePreset) -> None:
        """DefinitionとPreset keyの対応を呼び出し元のTransaction内へ登録する。

        Component順序とoptional commandを含むDefinitionとPreset key対応が完全に一致する
        再登録では既存値を維持する。Definition構成の不一致、Preset keyの付け替え、または
        Definition IDの別Preset keyへの再対応付けはWorkspacePresetConflictErrorとして拒否する。
        既存値と未指定のCatalog項目は更新・削除せず、Repository自身はTransactionをcommitまたは
        rollbackしない。
        """
