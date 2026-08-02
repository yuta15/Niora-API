# データベース設計

Niora APIで使用するデータベースの設計を記録します。

## データベース

- 製品：MySQL
- バージョン系列：9.7 LTS
- パッチバージョン：デプロイ時点の最新GAリリースへ固定する

採用理由とバージョン方針は、[ADR 0005](adr/0005-use-mysql-9.7-lts.md)を参照してください。

## 接続

- Database Schemaと永続化Model：SQLModel
- 接続プール：SQLModelが基盤とするSQLAlchemy 2.xの同期API
- DBAPI Driver：PyMySQL
- Storage Engine：InnoDB
- 文字コード：`utf8mb4`
- `Engine`と`sessionmaker`：Application Processごとに1つ
- `Session`：UseCase実行ごとに1つ

Transaction境界はUseCaseが担います。同じUseCaseで使用するRepositoryは同じ`Session`を共有します。Repositoryは`commit`、
`rollback`、`Session`の生成を行わず、Applicationが定義するUnit of WorkのPortを通してUseCaseがTransactionを管理します。
DomainとApplicationはMySQL、SQLModel、SQLAlchemy、PyMySQLの型へ依存しません。

SQLModelのTable ModelはMySQL Adapter内へ配置し、Domain EntityやAPI Schemaには使用しません。AdapterでDomainの型と相互変換します。

接続プールでは接続取得時の死活確認と接続の再利用上限を有効にします。プールサイズ、Overflow、Timeout、再利用上限は、
Application Processの同時実行数とMySQLの最大接続数に合わせて設定します。

詳細と判断理由は[ADR 0008](adr/0008-use-sqlmodel-pymysql-and-alembic.md)を参照してください。

## マイグレーション

Schema変更にはPythonのSQLAlchemy EcosystemでデファクトスタンダードとなっているAlembicを使用し、単一の連続した
Revision履歴をリポジトリで管理します。

- 新しいRevisionは`uv run alembic revision --autogenerate -m "<message>"`で下書きを生成し、内容をレビューする
- ローカルとCIは`uv run alembic upgrade head`で適用する
- デプロイではAPIとScheduled Jobの更新前に専用Migration Jobで`uv run alembic upgrade head`を1回だけ実行する
- Application起動時にはMigrationを実行しない
- 空のDatabaseへ`head`まで適用できる状態を維持する
- Alembicの`target_metadata`へ`SQLModel.metadata`を指定し、`SQLModel.metadata.create_all()`は使用しない

MySQLのDDLはTransaction中でも暗黙にcommitされるため、複数のSchema変更をまとめてrollbackできるとはみなしません。
破壊的変更ではBackup、互換期間、復旧手順を定め、Production相当環境の復旧は原則として前方修正します。

## 設定

Database接続には次の設定値を使用します。

| 設定値 | 秘密情報 | 用途 |
| --- | --- | --- |
| `NIORA_DATABASE_HOST` | いいえ | MySQLのHost |
| `NIORA_DATABASE_PORT` | いいえ | MySQLのPort |
| `NIORA_DATABASE_NAME` | いいえ | 接続先Database名 |
| `NIORA_DATABASE_USER` | はい | MySQL Account名 |
| `NIORA_DATABASE_PASSWORD` | はい | MySQL AccountのPassword |
| `NIORA_DATABASE_POOL_SIZE` | いいえ | 通常保持する接続数 |
| `NIORA_DATABASE_MAX_OVERFLOW` | いいえ | 一時的に追加できる接続数 |
| `NIORA_DATABASE_POOL_TIMEOUT_SECONDS` | いいえ | 接続取得の待機上限 |
| `NIORA_DATABASE_POOL_RECYCLE_SECONDS` | いいえ | 接続を再作成するまでの秒数 |

ローカルではGit管理外の`.env`、デプロイでは非秘密情報をConfigMap、UserとPasswordをKubernetes Secretから渡します。
API用とMigration用のAccountおよびSecretを分離し、Migration用AccountだけにDDL権限を与えます。

Secretの実値、値を設定済みのManifest、接続URLをリポジトリへ保存しません。設定Object、環境変数、接続URL、SQLのParameterを
ログへ出力せず、SQLAlchemyのSQL Echoは既定で無効にします。

## 未決定事項

- ER図
- テーブルとカラムの定義
- インデックスと制約
- Productionで稼働中のRevisionからリリース対象Revisionまでを、既存データを含む状態でCI検証する方法
- 検証中に作成したProduction未適用のRevisionを、リリース前に統合または作り直す基準と、確定したMigration経路の再検証方法
- Applicationの新旧VersionとSchemaの互換性を維持する期間、および破壊的変更を適用できる条件
- Schema変更ごとに、Applicationの切り戻し、Schemaの可逆性、データの復元方法、前方修正の手順を評価する方法
- バックアップとリストア
