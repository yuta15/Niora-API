from src.shared.infra.database import Base


def test_base_metadata_success_defines_constraint_naming_convention() -> None:
    """共通Metadataがすべての制約種別に安定した命名規則を提供することを確認する。"""
    assert Base.metadata.naming_convention == {
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
