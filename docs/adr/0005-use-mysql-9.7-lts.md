# 0005: データベースにMySQL 9.7 LTSを採用する

## 背景

Niora APIでは、教科書、章、WorkspaceDefinition、Workspaceなどのデータを永続化するリレーショナルデータベースが必要になる。

データベースにはMySQLとPostgreSQLを検討した。このプロジェクトは1人で開発・運用し、コスト効率、単純性、開発効率を優先する。

現在想定している小規模な構成と機能要件はMySQLで満たせる。PostgreSQLを採用しても、現時点ではPostgreSQL固有の機能を活用する予定がなく、学習、設計、運用上の選択肢が増えることで認知負荷が高くなると判断した。

MySQLには、安定した機能と長期サポートを提供するLTS系列と、新機能や変更を継続的に取り込むInnovation系列がある。

## 決定

Niora APIのデータベースにMySQL 9.7 LTSを採用する。

- MySQL 9.7.x LTS系列を使用する
- デプロイ時は、9.7.x系列でリリース済みの最新GAパッチバージョンへ固定する
- 未リリースのパッチバージョンは使用しない
- Innovation系列へ自動的に移行しない
- 次のLTS系列へ移行する場合は、互換性、移行手順、運用コストを再評価して新しいADRを作成する

## 代替案

### PostgreSQL

PostgreSQLを利用する案。

必要な機能を満たせるが、現時点ではPostgreSQL固有の機能を必要としていない。小規模な個人開発に対して学習、設計、運用上の認知負荷が増える一方、得られる利点が少ないと判断したため採用しない。

### MySQL Innovation系列

MySQLの最新Innovation系列を利用する案。

新しい機能を早く利用できる一方、更新頻度と動作変更への追従コストが増える。Niora APIでは新機能より安定性と運用負荷の低さを優先するため採用しない。

## 影響

- スキーマ、SQL、マイグレーションはMySQL 9.7の仕様を基準にする
- データベース固有の処理はAdapter内に配置し、DomainとApplicationへMySQLの詳細を持ち込まない
- 同じ9.7 LTS系列内でも、パッチ更新前にバックアップと互換性確認が必要になる
- PostgreSQL固有の機能やSQLは利用できない
- 将来データベースを変更する場合は、データ移行とAdapterの差し替えが必要になる

## 参考

- [MySQL 9.7 LTSリリース](https://blogs.oracle.com/mysql/mysql-9-7-0-lts-is-now-available-expanded-community-capabilities-and-dynamic-data-masking-for-enterprise)
- [MySQLのLTSとInnovationリリース](https://dev.mysql.com/doc/refman/9.7/en/mysql-releases.html)
- [MySQL 9.7リリースノート](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/)
