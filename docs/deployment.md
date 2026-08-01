# デプロイと運用

Niora APIのデプロイ方法と運用手順を記録します。

デプロイ先にはk3sを使用します。Namespace、配置、Workspaceの期限切れ削除については、[アーキテクチャ](architecture.md)を参照してください。

## 配置

| Namespace | Workload |
| --- | --- |
| `ns-niora-service` | フロントエンド、Niora API、MySQL、期限切れ削除CronJob |
| `ns-niora-workspaces` | Workspaceを構成するPod群と付随するリソース |

## 未決定事項

- リリース手順
- 環境変数とシークレットの管理
- CronJobの実行間隔と完了したJobの保持期間
- ログとモニタリング
- 障害対応
- ロールバック手順
