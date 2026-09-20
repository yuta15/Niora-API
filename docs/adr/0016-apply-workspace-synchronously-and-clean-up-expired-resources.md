# 0016: Workspaceを同期適用し期限切れリソースを回収する

## 背景

Workspaceは複数のk3sリソースで構成され、作成や削除の途中で失敗することがある。v0.0.1ではApply Job、未収束Workspaceの定期再適用、full reconcile、outbox/dispatcher、driftや欠損の修復を行わず、APIからRuntimeへ同期的に一度操作を依頼する。Database transactionとk3s I/Oは分離し、操作失敗後に残るSessionまたはリソースは有効期限後の共通Cleanupで回収できるようにする。

## 決定

### 状態と責務

- WorkspaceDefinitionは不変な作成構成を表し、WorkspaceSessionはApplicationがRuntime操作前に保存する利用単位のmetadataを表す。Sessionの存在はRuntimeの作成成功を保証しない。
- k3s上のリソースを実行状態のobserved stateとする。Databaseはk3sを継続収束させるdesired stateではない。
- 全k3s resourceに`managed-by` label、WorkspaceSession ID label、およびUTCの`expires_at` annotationを作成時に付与する。必要なmetadataの欠落または不正を検出した場合は警告する。Database Sessionが存在しない孤立resourceは、必要なmetadataが正しい場合だけ自動削除する。
- Runtimeの作成操作はWorkspaceSessionとWorkspaceDefinitionを受け取る。観測操作はk3sのobserved stateだけを返し、Database由来のSessionまたはDefinitionを返さない。

### Create

1. 短い読取Unit of WorkでPresetからDefinition IDを解決し、対応するWorkspaceDefinitionを取得してWorkspaceSessionを生成する。
2. 短い書込Unit of WorkでWorkspaceSessionを保存する。
3. Database transactionの外でRuntimeへ一度だけ同期作成を依頼する。

Session保存に失敗した場合はRuntimeを呼ばず、元のエラーを返す。Runtime作成に失敗した場合は元のエラーを返し、保存済みSessionや作成途中のresourceを即時に補償・再試行・収束させない。これらは有効期限後のCleanup対象とする。k3s I/O中にDatabase transactionを保持しない。

### DeleteとGet

- Deleteはまず短い読取Unit of WorkでDatabase上のWorkspaceSessionを確認する。存在しない場合は完了とする。期限切れの場合はRuntimeとDatabase Sessionを操作せず、期限Cleanupへ委譲する。期限内の場合はtransaction外でSession ID labelを使って同期削除し、対象がk3sに存在しない場合も成功とする。Runtime削除成功後に短いUnit of WorkでDatabase Sessionを削除する。
- Runtime削除が失敗した場合はDatabase Sessionを維持する。Runtime削除後のDatabase削除が失敗した場合はAPI errorとし、再Deleteで回復する。作成処理は行わない。
- GetはDatabaseのWorkspaceSessionとWorkspaceDefinition、およびk3sのobserved stateを組み合わせて返す。Database Sessionがなければnot foundとし、Sessionがあり対応リソースが欠損している場合は欠損状態として表現する。Getで修復しない。

### 期限Cleanup

APIと同じ成果物を使うWorkspace Cleanup CronJobを設け、別Entrypointから期限切れ対象を回収する。対象は、(a) Databaseの`expires_at`を過ぎたWorkspaceSessionと、(b) k3sの`expires_at` annotationを過ぎた管理対象resourceの和集合とする。Database Sessionが存在する場合はDatabaseの期限を優先し、期限前ならannotationが期限切れでも削除せず不一致を警告する。Database Sessionが期限切れなら、正しい`managed-by` labelとSession ID labelを持つresourceを削除し、期限annotationの欠落または不一致は警告する。Database Sessionが存在しない場合だけ、同じSession IDを持つresourceの有効な期限annotationが一致し、すべて期限切れであることを確認して孤立resourceを削除する。

各対象についてRuntimeリソースを削除し、その後Database Sessionを削除する。対象ごとの失敗は記録して、ほかの対象の処理を継続する。

Cleanupは期限前の明示Delete失敗を再試行しない。また、欠損リソースの修復、driftの修復、resourceの更新または再作成を行わない。

### Transaction境界

各Database transactionはUnit of Workで管理する。原則としてUseCase単位だが、CreateとDeleteでは外部I/Oを挟む複数の短いtransactionを使用できる。外部I/O中にtransactionを保持しない。

### ADR 0014から維持する判断

ADR 0014のdesired state、Job適用、定期reconcile、削除順序、およびそれらの影響に関する決定を本ADRで置き換える。WorkspaceDefinitionとWorkspaceSessionの永続化、Presetとの境界、不変Definition、Kustomizeを使わないこと、およびDefinitionからk3s resourceを直接生成することは維持する。

## 代替案

### Apply Job、outbox/dispatcher、定期reconcileで継続的に収束させる

処理再試行やdrift修復を提供できる一方、Job起動、outbox配送、再試行、定期走査および並行実行の運用責務が加わる。v0.0.1では同期操作と期限Cleanupに限定する。

### k3s I/OをDatabase transaction内で行う

外部APIの遅延や失敗の間、Database transactionと接続を保持するため採用しない。

### Cleanupで期限前の失敗やdriftも修復する

期限切れ回収を越えてWorkspaceを継続管理する仕組みとなる。v0.0.1の責務に含めない。

## 影響

- APIの作成・削除はk3sの同期応答を待つため、処理時間が長くなる可能性がある。
- Databaseとk3sをまたぐ原子的な更新はない。Runtime作成失敗後もSessionだけ、または作成途中のresourceだけが期限まで残る可能性があり、APIは元のエラーを返す。
- 明示Deleteの失敗はSessionを維持し、期限Cleanupの対象となるまでは自動再試行しない。
- Database Sessionがない孤立resourceは、期限metadataが正しい場合だけ回収する。Database Sessionが期限切れの場合はDatabase期限を優先し、正しい管理Labelを持つresourceを回収する。
- Database transactionを短く保ち、外部I/O中の接続占有を避けられる。
- 欠損やdriftの修復、期限前の再試行、resourceの更新・再作成は提供しない。

## 関連ドキュメント

- [Workspaceのdesired stateを永続化しJobでk3sへ収束させる（履歴）](0014-persist-workspace-desired-state-and-apply-with-jobs.md)
- [Workspace system presetをJSON CatalogとしてGit管理する](0015-manage-workspace-system-presets-as-json-catalog.md)
- [現在のアーキテクチャ](../architecture.md)
- [API実装規約](../api.md)
