# デプロイと運用

Niora APIのデプロイ方法と運用手順を記録します。

デプロイ先にはk3sを使用します。Namespace、配置、Workspaceの期限切れ削除については、[アーキテクチャ](architecture.md)を参照してください。

## 配置

| Namespace | Workload |
| --- | --- |
| `ns-niora-service` | フロントエンド、Niora API、MySQL、期限切れ削除CronJob |
| `ns-niora-workspaces` | Workspaceを構成するPod群と付随するリソース |

## Database Migration

APIと期限切れ削除CronJobの更新前に、同じApplication Imageを使用する単発のMigration Jobで
`uv run alembic upgrade head`を実行します。Migrationが成功した場合だけ後続Workloadを更新し、Application起動時には
Migrationを実行しません。

Migration JobはDDL権限を持つ専用MySQL Accountを使用します。APIと期限切れ削除CronJobは、実行に必要なDML権限だけを持つ
別のAccountを使用します。

## 設定とSecret

DatabaseのHost、Port、Database Name、接続プール設定はConfigMap、UserとPasswordはKubernetes Secretから環境変数として
対象Containerだけへ渡します。API用とMigration用のSecretを分離し、Migration用SecretはMigration Jobだけへ渡します。

Secretの値はリポジトリ内のManifestへ記載せず、デプロイ前にリポジトリ外から作成します。Secretはbase64 encodingだけでは
暗号化されないため、k3sの保存時暗号化と最小権限のRBACを有効にします。Secret、接続URL、設定Objectをログへ出力しません。

## 未決定事項

- Git Commit、Application Image Digest、AlembicのTarget Revisionを同じリリースとして固定し、検証済みの成果物をProductionへ昇格する方法
- Migration Jobの起動主体、承認、排他制御、Timeout、再実行、および後続Workloadを更新するまでのリリース手順
- Production DatabaseのCurrent Revisionが想定と異なる場合にMigrationとデプロイを中止する仕組み
- 稼働中の旧ApplicationとMigration後のSchemaが共存する期間のデプロイ順序、および互換性を維持できない変更の適用方法
- CronJobの実行間隔と完了したJobの保持期間
- ログとモニタリング
- Migration失敗時に書き込み停止、再実行、前方修正、Backupからの復元を選択する基準と障害対応手順
- リリースごとにApplicationとDatabaseの切り戻し可能範囲、切り戻し不能になる時点、復旧手順を策定して検証する方法
