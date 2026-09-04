# 0012: SQLAlchemyを直接使用しDatabase Infrastructureの所有境界を分ける

## 背景

[ADR 0008](0008-use-sqlmodel-pymysql-and-alembic.md)では、Database Schemaと永続化Modelの定義にSQLModelを使用することを
決定した。その後、NioraではDomain Entity、Application Model、API Schema、Database Table Modelを責務ごとに分離し、
レイヤー間で共有せず明示的に変換する方針が明確になった。

SQLModelはPydanticとSQLAlchemyを統合したModelを提供するが、NioraではDatabase Table ModelをAPIの入力検証やSerializationに
使用しない。この構成ではSQLModelによる定義共有の利点が小さく、Database固有の型、制約、Index、Mappingを扱うために
基盤となるSQLAlchemyの知識と設定が引き続き必要になる。

また、すべてのTable ModelをAlembicの単一Revision履歴で管理するには共通の`MetaData`が必要になる。一方で、共通化を理由に
各Domain Moduleが所有するTable Modelまで共有Packageへ集約すると、Database上の所有境界が不明確になる。このため、共通の
Database技術基盤とModule固有のTable Modelを分ける必要がある。

## 決定

### SQLAlchemyの直接利用

Database Schemaと永続化Modelの定義には、SQLModelではなくSQLAlchemy 2.x ORMの型Annotation付きDeclarative Mappingを
直接使用する。Table Modelは`DeclarativeBase`を基底とし、`Mapped`と`mapped_column`を使用して定義する。

Database Table ModelはDomain Entity、Application Model、API Schemaと共有しない。APIの入力検証とSerializationには
引き続きPydanticを使用し、Database Table Modelには使用しない。DomainとApplicationはSQLAlchemyへ依存しない。

本ADRは、ADR 0008のSQLModelを採用する決定を置き換える。ADR 0008で決定したPyMySQL、同期`Session`、UseCase単位の
Transaction境界、Alembic、Secret管理、および実際のMySQLを使用するIntegrationテストの方針は維持する。

### Database Infrastructureの所有境界

すべてのDatabase Table Modelが共有するDeclarative Base、`MetaData`、Constraint命名規則はShared Infrastructureが所有する。
加えて、Domain Moduleに依存せず、複数のModuleから共通利用する汎用的かつ横断的なDatabase技術基盤もShared Infrastructureが
所有する。Shared InfrastructureにはDomain Module固有のTable Modelを置かない。

Textbookや将来のほかのDomain Moduleが所有するTable Modelは、それぞれのModuleのInfrastructure内へ配置する。Textbookと
ChapterのTable ModelはTextbook Infrastructureが所有し、Shared InfrastructureがTextbookのTable定義へ依存しない。

本ADRで決定するModule固有のDatabase InfrastructureはTable Modelの配置境界であり、Repository実装の配置は決定しない。

### Alembicとの連携

Alembicの`target_metadata`にはShared Infrastructureが提供するDeclarative Baseの`MetaData`を指定する。Migration実行時に
各ModuleのTable Modelを読み込み、同じ`MetaData`へ登録されたすべてのTableを単一の連続したRevision履歴で管理する。

Database SchemaはAlembic Revisionを正とし、Application起動時に`MetaData.create_all()`やMigrationを自動実行しない。

## 代替案

### SQLModelを継続して使用する

ADR 0008の決定を維持する案。

Database Table ModelとPydantic Modelを共有する構成では定義量を減らせるが、NioraはレイヤーごとにModelを分離する。
SQLAlchemy固有の機能を利用するとSQLModelとSQLAlchemyの両方を理解する必要もあるため、SQLAlchemyを直接使用する。

### ModuleごとにDeclarative Baseを持つ

各Domain Moduleが独立したDeclarative Baseと`MetaData`を持つ案。

Tableの所有境界は明確になるが、Alembicへ複数の`MetaData`を集約する構成が必要になり、Constraint命名規則もModule間で
重複管理することになる。Nioraは1つのDatabaseと単一のRevision履歴を使用するため、技術基盤だけをShared Infrastructureで
共有する。

### すべてのTable ModelをShared Infrastructureへ置く

Declarative BaseとすべてのTable Modelを1つのPackageへ集約する案。

Alembicからは読み込みやすいが、Textbookなど各Domain Moduleが所有するデータの境界が失われる。Shared Infrastructureには
共通の技術基盤だけを置き、Table Modelは所有するModuleへ配置する。

## 影響

- ADR 0008のSQLModel採用部分は本ADRによって置き換えられる
- SQLAlchemyをApplicationの直接依存ではなくInfrastructureの実装詳細として扱う必要がある
- Shared InfrastructureはDomain Moduleに依存しない、汎用的かつ横断的なDatabase技術基盤を提供する
- Module固有のTable Modelは各ModuleのInfrastructureが所有する
- Alembic実行時には、すべてのModuleのTable Modelを確実に読み込んで共通の`MetaData`へ登録する必要がある
- SQLModelと比較してTable Modelの定義量は増えるが、Database固有のMappingと制約を明示できる
- Table ModelとDomain Entityの変換はDatabase境界の実装で行う必要がある
- 新しいDomain ModuleがTableを追加するときも、Shared InfrastructureへTable Modelを追加しない

具体的なPackage構成、Table、Column、Index、ConstraintおよびMigration手順は、
[データベース設計](../database.md)で管理する。

## 関連ドキュメント

- [アーキテクチャ](../architecture.md)
- [データベース設計](../database.md)
- [ADR 0004: ソフトウェア構成にクリーンアーキテクチャを採用する](0004-use-clean-architecture.md)
- [ADR 0008: Database SchemaにSQLModel、MySQL接続にPyMySQL、MigrationにAlembicを採用する](0008-use-sqlmodel-pymysql-and-alembic.md)
- [SQLAlchemy Declarative Mapping](https://docs.sqlalchemy.org/en/20/orm/declarative_mapping.html)
