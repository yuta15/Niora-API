# 0008: Database SchemaにSQLModel、MySQL接続にPyMySQL、MigrationにAlembicを採用する

> SQLModelを採用する決定は[ADR 0012](0012-use-sqlalchemy-and-separate-database-infrastructure.md)で置き換えた。
> PyMySQL、Transaction境界、Alembic、Secret管理、Integrationテストに関する決定は引き続き有効とする。

## 背景

Niora APIでは、Textbook、Chapter、WorkspaceDefinitionなどの永続データをMySQL 9.7 LTSへ保存する。
ADR 0004ではDomainとApplicationを外部技術から分離することを、ADR 0005ではMySQL 9.7 LTSを使用することを決定した。

PythonからMySQLへ接続する方法、Database SchemaとMigrationの管理方法、Transaction境界、Secretの受け渡し方、
Integrationテストで使用するMySQLの起動方法は未決定だった。これらの方式を決定し、実装時に守る境界を明確にする必要がある。

## 決定

### Database SchemaとMySQL接続

Database Schemaと永続化Modelの定義にSQLModel、MySQLのDBAPI DriverにPyMySQLを使用する。

SQLModelはFastAPIとの組み合わせを想定して設計され、PydanticとSQLAlchemyを基盤としている。既存のFastAPI、Pydantic、
Pythonの型Annotationと一貫した書き方ができ、学習する概念とSchema定義の重複を減らせるため採用する。

PyMySQLはPure Pythonで動作し、OS固有のClient LibraryやBuild環境を必要としない。v0.0.1ではDriverの性能より、
ローカル、CI、Containerで同じ手順を利用できることを優先する。

SQLModelのTable ModelとPyMySQLへの依存はMySQL Adapter内に限定する。DomainとApplicationはSQLModel、SQLAlchemy、
PyMySQLへ依存せず、RepositoryなどのApplication PortとDomainの型だけを使用する。

### Transaction境界

Transaction境界はUseCaseが担い、1回のUseCase実行を1つのTransactionとする。同じUseCaseで使用するRepositoryは、
同じTransactionへ参加する。

Repositoryは永続化操作だけを担当し、Transactionの開始、commit、rollbackを判断しない。更新系UseCaseは必要な処理が
すべて成功した場合だけcommitし、失敗時はすべての変更をrollbackする。UseCaseはUnit of WorkをContext Managerとして
`with unit_of_work:`で利用し、Context Managerの終了処理にcommitとrollbackを集約する。正常終了時は自動的にcommitし、
処理中に例外が発生した場合は自動的にrollbackするため、UseCaseから明示的にcommitを呼び出さない。

Unit of WorkはApplicationが定義する抽象Portとし、Transactionのcommitとrollbackの振る舞いだけを提供する。Sessionの生成と
解放、およびRepositoryの保持と生成はUnit of Workの責務に含めず、Database InfrastructureとDependency Injectionが担当する。

### Migration

Database MigrationにはAlembicを使用し、Revisionをリポジトリで管理する。

AlembicはPythonのSQLAlchemy Ecosystemでデファクトスタンダードとなっており、SQLModelのMetadataを利用してRevisionの生成、
履歴管理、適用ができるため採用する。Database SchemaはAlembic Revisionを正とし、Application起動時に
`SQLModel.metadata.create_all()`やMigrationを自動実行しない。MigrationはApplicationの起動や更新と分離して明示的に実行する。

### 設定値とSecret

Database接続設定は実行環境から受け取る。ローカルではGit管理外の`.env`、デプロイ環境では非秘密情報をConfigMap、
認証情報をKubernetes Secretから対象Containerへ渡す。

Secretの実値、値を設定済みのManifest、接続URLをリポジトリへ保存しない。Secret、接続URL、設定Object、SQLのParameterを
ログへ出力しない。

### Integrationテスト

MySQL AdapterのIntegrationテストでは、SQLiteやDBAPIのMockで代替せず、デプロイ対象と同じMySQL 9.7 LTS系列の
公式Container ImageをDocker Composeで起動して使用する。ローカルとCIで同じ起動方式を使用する。

## 代替案

### SQLAlchemy ORMを直接使用する

SQLAlchemyのDeclarative ModelでDatabase Schemaを定義する案。

複雑なMappingでは柔軟性が高いが、v0.0.1で必要なSchemaはSQLModelで表現できる。FastAPI、Pydantic、Pythonの
型Annotationと一貫した学習しやすいAPIを優先するため採用しない。

### SQLModelの非同期Sessionとasyncmyを使用する

非同期I/OでMySQLへ接続する案。

現在のUseCase、Repository、APIは同期Interfaceで構成されている。v0.0.1では非同期化の複雑さに見合う効果を見込めないため
採用しない。Database待ちが性能上の問題になった場合に、計測結果をもとに再評価する。

### Application起動時にSchemaを作成・更新する

Application起動時に`SQLModel.metadata.create_all()`またはAlembicを実行する案。

複数Processによる同時実行、ApplicationへのDDL権限の付与、起動失敗とMigration失敗の混在が生じるため採用しない。

### IntegrationテストでSQLiteまたはMockを使用する

MySQLを起動せずにIntegrationテストを実行する案。

MySQL固有の型、制約、Transaction、Errorを検証できないため採用しない。

## 影響

- DomainとApplicationをMySQL、SQLModel、SQLAlchemyから独立させた構成を維持する必要がある
- SQLModelのTable ModelとDomain EntityをMySQL Adapterで相互変換する必要がある
- 複数Repositoryを操作するUseCaseでは、同じTransactionへ参加させる仕組みが必要になる
- Schema変更はAlembic Revisionとして作成し、Applicationとは別に適用する必要がある
- ローカルとCIでIntegrationテストを実行するにはDockerが必要になる
- Secretをリポジトリやログへ出力しない設定と運用が必要になる

接続設定、Migration手順、デプロイ方法、Integrationテストの分離と後始末は、それぞれ
[データベース設計](../database.md)、[ローカル開発ガイド](../development.md)、[デプロイと運用](../deployment.md)、
[テスト方針](../testing.md)で管理する。

## 参考

- [SQLModel](https://sqlmodel.tiangolo.com/)
- [SQLModel: Features](https://sqlmodel.tiangolo.com/features/)
- [SQLAlchemy: MySQL and MariaDB](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)
- [Alembic Documentation](https://alembic.sqlalchemy.org/en/latest/)
- [Docker Compose: Control startup and shutdown order](https://docs.docker.com/compose/how-tos/startup-order/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
