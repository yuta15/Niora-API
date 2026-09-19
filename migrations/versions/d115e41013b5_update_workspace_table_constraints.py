"""テーブル定義変更

Revision ID: d115e41013b5
Revises: b46288897efb
Create Date: 2026-09-19 11:38:48.470972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "d115e41013b5"
down_revision: Union[str, Sequence[str], None] = "b46288897efb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Catalog識別子の大文字小文字区別と一対一制約を適用する。"""
    op.alter_column(
        "preset_workspace_definition_mapping",
        "preset_key",
        existing_type=mysql.VARCHAR(length=128),
        type_=mysql.VARCHAR(length=512, collation="utf8mb4_0900_bin"),
        existing_nullable=False,
    )
    op.drop_index("uq_preset_key_definition_id", table_name="preset_workspace_definition_mapping")
    op.create_unique_constraint(
        op.f("uq_preset_workspace_definition_mapping_definition_id"),
        "preset_workspace_definition_mapping",
        ["definition_id"],
    )

    op.drop_constraint(
        op.f("fk_terminal_access_point_table_definition_id_workspace_component"),
        "terminal_access_point_table",
        type_="foreignkey",
    )
    op.alter_column(
        "workspace_component",
        "component_key",
        existing_type=mysql.VARCHAR(length=128),
        type_=mysql.VARCHAR(length=128, collation="utf8mb4_0900_bin"),
        existing_nullable=False,
    )
    op.alter_column(
        "terminal_access_point_table",
        "component_key",
        existing_type=mysql.VARCHAR(length=128),
        type_=mysql.VARCHAR(length=128, collation="utf8mb4_0900_bin"),
        existing_nullable=False,
    )
    op.create_foreign_key(
        op.f("fk_terminal_access_point_table_definition_id_workspace_component"),
        "terminal_access_point_table",
        "workspace_component",
        ["definition_id", "component_key"],
        ["definition_id", "component_key"],
        ondelete="CASCADE",
    )

    op.alter_column(
        "workspace_component",
        "image",
        existing_type=mysql.VARCHAR(length=128),
        type_=sa.String(length=512),
        existing_nullable=False,
    )
    op.alter_column(
        "chapter",
        "workspace_preset_key",
        existing_type=mysql.VARCHAR(length=128),
        type_=sa.String(length=512),
        existing_nullable=True,
    )


def downgrade() -> None:
    """識別子の照合順序と制約を旧Schemaへ戻す。"""
    # 後方互換の文字数拡張は、既存データの切り捨てを避けるため維持する。
    op.drop_constraint(
        op.f("fk_terminal_access_point_table_definition_id_workspace_component"),
        "terminal_access_point_table",
        type_="foreignkey",
    )
    # op.alter_column(
    #     "terminal_access_point_table",
    #     "component_key",
    #     existing_type=mysql.VARCHAR(length=128, collation="utf8mb4_0900_bin"),
    #     type_=mysql.VARCHAR(length=128, collation="utf8mb4_0900_ai_ci"),
    #     existing_nullable=False,
    # )
    # op.alter_column(
    #     "workspace_component",
    #     "component_key",
    #     existing_type=mysql.VARCHAR(length=128, collation="utf8mb4_0900_bin"),
    #     type_=mysql.VARCHAR(length=128, collation="utf8mb4_0900_ai_ci"),
    #     existing_nullable=False,
    # )
    op.create_foreign_key(
        op.f("fk_terminal_access_point_table_definition_id_workspace_component"),
        "terminal_access_point_table",
        "workspace_component",
        ["definition_id", "component_key"],
        ["definition_id", "component_key"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        op.f("fk_preset_workspace_definition_mapping_definition_id_workspace_definition"),
        "preset_workspace_definition_mapping",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("uq_preset_workspace_definition_mapping_definition_id"),
        "preset_workspace_definition_mapping",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_preset_key_definition_id",
        "preset_workspace_definition_mapping",
        ["preset_key", "definition_id"],
    )
    op.create_foreign_key(
        op.f("fk_preset_workspace_definition_mapping_definition_id_workspace_definition"),
        "preset_workspace_definition_mapping",
        "workspace_definition",
        ["definition_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # op.alter_column(
    #     "preset_workspace_definition_mapping",
    #     "preset_key",
    #     existing_type=mysql.VARCHAR(length=512, collation="utf8mb4_0900_bin"),
    #     type_=mysql.VARCHAR(length=512, collation="utf8mb4_0900_ai_ci"),
    #     existing_nullable=False,
    # )
