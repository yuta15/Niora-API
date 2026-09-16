from src.shared.application.ports import UnitOfWork
from src.workspace.application.ports import WorkspacePresetRepository
from src.workspace.domain import WorkspacePresetProvider


class RegisterWorkspacePresets:
    """提供されたWorkspacePreset Catalogを永続化する。"""

    def __init__(
        self,
        workspace_preset_provider: WorkspacePresetProvider,
        workspace_preset_repository: WorkspacePresetRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._workspace_preset_provider = workspace_preset_provider
        self._workspace_preset_repository = workspace_preset_repository
        self._unit_of_work = unit_of_work

    def execute(self) -> None:
        """Catalogを定義順に1つのTransaction内で登録する。"""
        with self._unit_of_work:
            for preset in self._workspace_preset_provider.list_presets():
                self._workspace_preset_repository.register(preset)
