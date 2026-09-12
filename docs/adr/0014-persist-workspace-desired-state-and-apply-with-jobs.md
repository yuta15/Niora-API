# 0014: Workspaceのdesired stateを永続化しJobでk3sへ収束させる

## 背景

Workspaceは、1つ以上のPodとNetworkPolicyなど複数のKubernetesリソースで構成される。これらの作成は原子的ではなく、
途中まで成功した時点でApplication Processまたは実行処理が終了する可能性がある。部分適用後に同じWorkspaceへ収束させるには、
実行基盤とは独立して、作成すべき構成を継続して取得できる必要がある。

[ADR 0009](0009-separate-workspace-domain-and-runtime-adapters.md)では、WorkspacePresetKeyから実行環境の詳細をInfrastructureが
解決し、WorkspaceDefinitionをDomainへ置かない方針を採用した。[ADR 0013](0013-manage-workspace-presets-as-kustomize-manifests.md)
では、Kustomize ManifestをPreset構成の正としている。しかし、この構成ではPreset解決、Manifest生成、期待状態の検証、
部分適用後の再試行がKubernetes Infrastructureへ集中する。また、ComponentとAccessPointをApplicationとDomainから扱えず、
将来ユーザー定義環境を追加するとPresetとは異なる実行契約が必要になる。

[ADR 0010](0010-store-workspace-session-metadata-in-k3s.md)ではWorkspaceSessionをMySQLへ保存せず、k3sリソースから復元する
方針を採用した。この方式では、すべてのリソースが失われた場合や作成前に処理が終了した場合に、作成すべきWorkspaceを
特定できない。k3s上の情報だけを使うと、期待する構成と観測した構成も独立して比較できない。

## 決定

### WorkspaceDefinition

`WorkspaceDefinition`をWorkspace Domainへ再導入し、利用者へ提供する実行環境の確定済み構成を表す不変なDomain Modelとする。

```text
WorkspaceDefinition
├── definition_id
└── components: NonEmpty[WorkspaceComponent]
    ├── component_key
    ├── image
    ├── startup_command: tuple[str, ...] | None
    └── terminal_exec: TerminalExecAccessPoint | None
```

- `definition_id`には永続化時に発行するUUIDを使用する
- WorkspaceDefinitionは作成後に変更せず、構成を変更するときは新しいIDのDefinitionを作成する
- revisionは持たない
- 同じ構成値を持つ別のDefinitionが存在することを許容し、IDで区別する
- 1件以上のWorkspaceComponentを持ち、`component_key`はDefinition内で一意とする
- Single ComponentとMulti Componentを別の型にせず、Component数の違いとして表現する
- v0.0.1では1 Componentを1コンテナ相当として扱う
- `TerminalExecAccessPoint`はComponentの子とし、Componentごとに最大1つだけ保持する
- Terminal接続先は`component_key`で特定し、`access_point_key`は持たない
- `image`にはRegistry、Repository、Digestを含む解決済みのOCI Image参照を保持し、Tagから実行時に再解決しない
- `startup_command`は未指定、またはShell文字列ではないargv全体として保持する

Pod、Service、NetworkPolicy、Label、AnnotationなどのKubernetes固有概念はWorkspaceDefinitionへ含めない。共通の
Security設定など、利用者へ提供する実行環境の構成ではないKubernetes固有PolicyはInfrastructureが扱う。

### Presetとの境界

WorkspacePresetは、システム提供WorkspaceDefinitionを生成するための入力であり、Domain Modelとしない。Preset固有の値は、
WorkspaceDefinitionを作成する前にApplicationがInfrastructureのPortを介して解決する。ImageはOCI Registry上のDigestへ固定し、
省略値や生成パラメータも確定させてからWorkspaceDefinitionを生成する。

生成したWorkspaceDefinitionと、WorkspacePresetKeyからDefinition IDへの対応をMySQLへ別々に保存する。1つの
WorkspacePresetKeyは1つのDefinition IDへ不変に対応させる。Presetの構成を変更するときは、新しいWorkspaceDefinitionと
新しいWorkspacePresetKeyを作成し、必要なChapterだけを新しいPresetKeyへ変更する。v0.0.1ではシステム提供Presetを
事前登録し、利用者によるPresetの登録や更新は提供しない。

将来ユーザー定義環境を追加する場合も、必要な値を解決した後は同じWorkspaceDefinitionを生成して永続化する。Definitionを
利用する処理へ、Presetまたはユーザー定義という供給元の違いを渡さない。

### desired stateとobserved state

WorkspaceDefinitionとWorkspaceSessionをMySQLへ永続化する。WorkspaceSessionは作成時に選択したDefinition IDを不変に参照し、
WorkspaceSession ID、有効期限、および実行環境を存在させるか削除するかというライフサイクル上の意図を保持する。

WorkspaceDefinitionとWorkspaceSessionの組み合わせを、作成、再適用、および削除へ収束させるdesired stateの正とする。
k3s上に存在するリソースをobserved stateの正とし、Podなどの実行状態をMySQLへ状態の正として複製しない。最終試行時刻や
エラーなどを運用情報として保存する場合も、実行状態の判断にはk3sから取得したobserved stateを使用する。

WorkspaceDefinitionまたはWorkspaceSessionをk3sリソース、Label、Annotation、リソース名から復元しない。k3s Metadataは、
MySQL上のdesired stateと実行中リソースを識別および照合するためだけに使用する。

Workspaceの一時ファイルなど、実行環境内の利用者データを永続化して再開する機能は引き続きv0.0.1の対象外とする。

### Jobによる適用

複数のKubernetesリソースを適用する処理は、常駐Controllerではなく、一回実行して終了するJobから行う。APIは
WorkspaceDefinitionとWorkspaceSessionをMySQLのTransactionで保存してCommitした後、WorkspaceSession IDを指定して
Apply Jobの起動を要求する。JobへWorkspaceDefinition、Preset、Manifestを受け渡さない。

Apply JobはInbound AdapterとしてApplicationの適用UseCaseを呼び出す。適用UseCaseはWorkspaceSession IDからMySQL上の
WorkspaceSessionとWorkspaceDefinitionを取得し、Infrastructure非依存のPortを通してk3sへ収束を要求する。

Kubernetes Infrastructureは、WorkspaceDefinitionとWorkspaceSessionから期待するリソース集合と適用順序を決定的に生成する。
リソースごとの論理キーとWorkspaceSession IDから名前を決定し、k3sから取得したobserved stateとの差分に応じて、存在する
リソースの維持、不足リソースの作成、更新、再作成、または不要リソースの削除を行う。

複数リソースの適用をTransactionとして扱わず、途中失敗時に適用済みリソースをRollbackしない。同じJobまたは後続Jobが、
MySQLから同じdesired stateを読み直し、k3sを再観測してリソース単位に再試行する。手続き的な適用済みStepを状態の正として
MySQLへ保存しない。

Job起動要求の失敗やJobのRetry上限到達後にもdesired stateを失わない。未収束のWorkspaceを検出して同じ適用UseCaseを再実行する
定期Jobを用意する。即時Jobと定期Jobが重複しても結果が変わらない契約とし、同じWorkspaceSessionを同時に操作する場合の
排他方式と具体的な実行間隔は後続Issueで決定する。

明示的な終了と期限切れも、WorkspaceSessionのライフサイクル上の意図をMySQLへ先に記録し、同じJob実行方式でk3s上の
リソース削除へ収束させる。

### Kustomizeとの関係

Workspace Runtimeのリソース生成にKustomizeを使用しない。Kubernetes InfrastructureがDomainのWorkspaceDefinitionから
Kubernetes Clientの型へ直接変換する。生成処理とk3s APIを操作する処理を分離し、WorkspaceDefinitionの値とManifestの値を
二重管理しない。

同じWorkspaceDefinitionとWorkspaceSession、および同じInfrastructure Policyからは、同じ論理リソース集合を生成する。
Definitionが所有する値を変更するときは新しいDefinitionを作成する。共通のKubernetes固有Policyを変更した場合は、既存Sessionも
新しいPolicyへ収束し得ることを許容する。

### レイヤー境界

- Domain: WorkspaceDefinition、WorkspaceComponent、AccessPoint、WorkspaceSessionと不変条件、observed stateの集約規則
- Application: Preset入力の解決とDefinition生成、DefinitionとSessionの永続化順序、Job起動の調整、desired/observed stateを使った処理調整
- Database Infrastructure: WorkspaceDefinition、Presetとの対応、WorkspaceSessionの保存と取得
- Job Inbound Adapter: WorkspaceSession IDを受け取り、Applicationの適用UseCaseを一回実行するEntrypoint
- Kubernetes Infrastructure: リソース生成、差分検出、適用、観測、削除

APIとJobは同じRepository、Workspaceモジュール、およびApplication Imageを使用し、別Processとして実行する。

## 置き換える決定

- [ADR 0009](0009-separate-workspace-domain-and-runtime-adapters.md)の、WorkspaceDefinitionをDomainへ置かず、Runtime InfrastructureがWorkspacePresetKeyから構成を解決する決定
- [ADR 0010](0010-store-workspace-session-metadata-in-k3s.md)の、WorkspaceSessionをMySQLへ保存せずk3s Metadataから復元する決定
- [ADR 0011](0011-compose-workspace-resource-lifecycle-steps.md)の、WorkspacePresetKeyからWorkspaceResourcePlanを解決し、手続き的なStep列を再試行単位とする決定
- [ADR 0013](0013-manage-workspace-presets-as-kustomize-manifests.md)の、WorkspacePresetとKustomize Manifestを構成の正とし、Workspace RuntimeでKustomizeを使用する決定

[ADR 0007](0007-run-workspaces-as-pods.md)の、1つ以上のPodでWorkspaceを構成し、k3sをobserved stateの正とする決定、
PodをDeploymentなどのControllerで自動再作成しない決定、およびPod execで接続する決定は維持する。Podなどの欠損を復元する
場合はNioraのJobを再実行する。

## 代替案

### PresetまたはKustomize Manifestをdesired stateの正とする

Preset解決とKubernetes固有の構成がRuntime Infrastructureへ集中し、Applicationが期待するComponentとAccessPointを扱えない。
将来ユーザー定義環境を追加した場合に利用側の契約も分岐するため採用しない。

### WorkspaceSessionをk3s Metadataだけに保存する

k3sリソースがすべて失われた場合や作成前に処理が終了した場合に、作成すべきWorkspaceを特定できない。部分適用後に期待構成と
観測構成を独立して比較できないため採用しない。

### API Processがk3sへ直接適用する

HTTP処理と複数リソースの適用、待機、再試行が同じProcessへ混在する。DB Commit後かつJob起動前の失敗は定期Jobで回収でき、
適用処理もJobのRetryとして分離できるため採用しない。

### 常駐Controllerで継続的に収束させる

変更検知の遅延を短くできるが、v0.0.1の規模に対して常駐Process、Queueまたは監視Loop、Leader Electionなどの運用対象が増える。
一回実行する即時Jobと定期Jobで必要な収束を実現できるため採用しない。

### Definition SnapshotをWorkspaceSessionへ埋め込む

同じDefinitionを複数Sessionへ重複して保存し、Definition単位で参照と保持を管理できない。WorkspaceSessionは不変なDefinition IDを
参照し、Definitionを独立して保存する。

### Definition IDとrevisionを使用する

同じIDのDefinitionを更新し、SessionがIDとrevisionを参照する案。Definition自体を不変とし、変更ごとに新しいIDを発行する方が、
同じIDで異なる構成が解決される可能性を排除できるため採用しない。

## 影響

- WorkspaceDefinition、WorkspacePresetKeyとの対応、およびWorkspaceSession用のTable、Repository、Migrationが必要になる
- APIはWorkspaceSessionの保存とk3s操作を1つのTransactionにせず、desired stateを先にCommitする必要がある
- Workspace作成APIは、k3sへの適用完了ではなく、Job起動要求までを扱う非同期処理になる
- Jobの重複実行、途中失敗、および不明な実行結果を前提に、適用処理をリソース単位で冪等にする必要がある
- k3s Metadataの欠落や不一致を検出する必要があるが、DefinitionまたはSessionの復元元にはしない
- OCI Image Digestを参照中はRegistryから削除しない運用が必要になる
- Preset追加時は、パラメータ解決、Definitionの不変条件、OCI Imageの存在、およびPresetKeyとの対応を検証する必要がある
- APIとJobは同じコードとMigrationを共有しつつ、異なるEntrypoint、権限、および実行時間制約を持つ
- Definition、Session、Job実行、Kubernetes変換、観測、状態集約を後続Issueへ分けて実装する必要がある

## 関連ドキュメント

- [v0.0.1の対象範囲](0001-define-version-0.0.1-scope.md)
- [モジュラーモノリス](0003-use-modular-monolith.md)
- [クリーンアーキテクチャ](0004-use-clean-architecture.md)
- [WorkspaceをPodで構成する](0007-run-workspaces-as-pods.md)
- [Workspaceの業務責務と技術責務](0009-separate-workspace-domain-and-runtime-adapters.md)
- [WorkspaceSessionの情報をk3sへ保持する](0010-store-workspace-session-metadata-in-k3s.md)
- [WorkspaceリソースのStep](0011-compose-workspace-resource-lifecycle-steps.md)
- [WorkspacePresetをKustomize Manifestで管理する](0013-manage-workspace-presets-as-kustomize-manifests.md)
