# ローカル開発ガイド

Niora APIをローカルで開発するための詳細な手順とルールを記録します。

基本的なセットアップとコマンドは、トップレベルの[README](../README.md)を参照してください。

## 記載する内容

- ローカルサービスの起動方法
- テストデータの準備
- デバッグ方法
- コーディング規約
- 開発時のトラブルシューティング

## Database設定

`.env.example`を`.env`へコピーし、ローカル専用のDatabase接続情報を設定します。`.env`はGit管理へ追加しません。
設定名と用途は[データベース設計](database.md#設定)を参照してください。

実装では`pydantic-settings`で各設定値を検証し、個別の値からSQLModelで使用する接続URLを組み立てます。接続URL、Password、
設定Objectをデバッグ出力しないでください。

## Database操作

MySQL AdapterとMigrationの実装時に、次の操作をMake targetとして提供します。

| 操作 | Make target | 内部で行う処理 |
| --- | --- | --- |
| 開発・Integrationテスト用MySQLの起動 | `make db-up` | 固定したMySQL 9.7 GA ImageをDocker Composeで起動し、Healthcheckを待つ |
| Migrationの適用 | `make migrate` | `uv run alembic upgrade head` |
| MySQLの停止とVolume削除 | `make db-down` | Docker ComposeのContainerとVolumeを削除する |

Integrationテストの標準実行順序は次のとおりです。

```bash
make db-up
make migrate
uv run pytest -m integration
make db-down
```

テスト失敗時も`make db-down`を実行します。Databaseごとの分離と後始末はpytest Fixtureが担当します。
