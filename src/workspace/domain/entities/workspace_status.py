from enum import StrEnum


class WorkspaceStatus(StrEnum):
    """Presetに依存しないWorkspaceの実行状態。"""

    PROVISIONING = "provisioning"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
