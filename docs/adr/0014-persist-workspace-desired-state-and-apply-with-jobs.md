# 0014: Workspaceのdesired stateを永続化しJobでk3sへ収束させる

> **後続の注記:** システム提供Workspace presetの保存形式は、[ADR 0015](0015-manage-workspace-system-presets-as-json-catalog.md)で
> Domain内のPython静的値から`catalog/system/workspace/presets.json`および`scripts/seed_system_catalog.py`へ移行した。
> WorkspacePresetProviderとDatabase上のdesired stateの契約は維持する。

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

`WorkspaceDefinition`をWorkspace Domainへ再導入し、利用者へ提供する実行環境の定義を表す不変なDomain Modelとする。

```text
WorkspaceDefinition
├── definition_id
└── components: NonEmpty[WorkspaceComponent]
    ├── component_key
    ├── image
    ├── startup_command: tuple[str, ...] | None
    └── terminal_exec: TerminalExecAccessPoint | None
        └── command: NonEmpty[tuple[str, ...]]
```

- `definition_id`にはUUIDを使用する
- システム提供PresetのWorkspaceDefinitionは、DomainのVersion管理されたDefinition Catalogに安定したUUIDを含め、同じPresetを再登録しても
  同じDefinition IDを使用する
- 将来ユーザー定義環境からWorkspaceDefinitionを作成する場合は、その作成時に新しいUUIDを発行する
- WorkspaceDefinitionは作成後に変更せず、構成を変更するときは新しいIDのDefinitionを作成する
- revisionは持たない
- 同じ構成値を持つ別のDefinitionが存在することを許容し、IDで区別する
- 1件以上のWorkspaceComponentを持ち、`component_key`はDefinition内で一意とする
- Single ComponentとMulti Componentを別の型にせず、Component数の違いとして表現する
- v0.0.1では1 Componentを1コンテナ相当として扱う
- `TerminalExecAccessPoint`はComponentの子とし、Componentごとに最大1つだけ保持する
- Terminal接続先は`component_key`で特定し、`access_point_key`は持たない
- `image`には実行に使用するOCI Imageを識別する空でない参照文字列を保持し、TagまたはDigestのどちらかへDomainでは制限しない
- OCI Imageの参照を別のDomain Modelへ分けず、実際に展開されたImage IDやDigestはk3sからobserved stateとして取得する
- `startup_command`は未指定、またはShell文字列ではない空でないargv全体として保持する
- `TerminalExecAccessPoint.command`は`/bin/bash`などTerminal接続時に実行する空でないargv全体として保持する
- argvの実行ファイルは空文字列を許可せず、各要素にNULを許可しない

Pod、Service、NetworkPolicy、Label、AnnotationなどのKubernetes固有概念はWorkspaceDefinitionへ含めない。共通の
Security設定など、利用者へ提供する実行環境の構成ではないKubernetes固有PolicyはInfrastructureが扱う。

### Presetとの境界

WorkspacePresetは、WorkspacePresetKeyと完成済みWorkspaceDefinitionを組として保持する不変なDomain Modelとする。
NioraがどのPresetを、どのKeyとDefinitionで提供するかはWorkspace Domainの知識であるため、システム提供Preset Keyと
WorkspaceDefinitionをDomain配下の別々のCatalogでGit管理する。Domain ServiceのWorkspacePresetProviderが両Catalogの対応を
保持し、利用側へ提供中のPreset Key一覧、すべてのWorkspacePreset、または指定KeyのWorkspacePresetを返す。
Preset入力Model、外部からPresetを取得するPort、およびPresetごとの登録入力は設けない。
PresetのWorkspaceComponentには実行に使用するOCI Image参照をそのまま保持し、OCI Registry上のDigestへ固定する処理は行わない。

Preset Key、WorkspaceDefinition、および両者の対応は不変なDomainデータとしてModule Scopeで保持する。
WorkspacePresetProviderのInstanceはGlobalに保持せず、DomainのFactoryで生成する。Applicationの構成時にFactoryを呼び出して
初期登録UseCaseへProviderを注入する。

WorkspacePresetProviderは、Preset KeyまたはDefinition IDの重複、対応が存在しないPreset Key、Presetから参照されないDefinition、
同じDefinitionを参照する複数Preset Keyを拒否する。これにより、Catalogの増減にかかわらず利用側の処理と取得方法を維持する。

初期登録UseCaseは登録対象のPresetを実行時の引数で受け取らず、構成時に注入されたWorkspacePresetProviderからWorkspacePresetをすべて取得して
永続化Portへ渡す。Database Infrastructureは受け取ったWorkspacePresetからWorkspaceDefinitionと、WorkspacePresetKeyから
Definition IDへの対応をMySQLへ別々に保存する。UseCaseはCatalog全体を1つのUnit of Workで処理し、同じTransactionで確定する。
同じCatalogの再登録は既存のDefinition IDと対応を維持する。既存のPresetKey、Definition ID、またはDefinitionの構成がProviderの
返すWorkspacePresetと一致しない場合は競合として登録全体を失敗させ、既存データを更新しない。

1つのWorkspacePresetKeyは1つのDefinition IDへ不変に対応させる。Presetの構成を変更するときは、新しい
WorkspaceDefinitionと新しいWorkspacePresetKeyをそれぞれのDomain Catalogへ追加してProviderで対応付け、必要なChapterだけを
新しいPresetKeyへ変更する。CatalogとProviderの対応からPresetを削除しても、登録済みのWorkspaceDefinitionまたは対応は削除しない。
v0.0.1では利用者によるPresetの登録や更新を提供しない。Workspace作成時はDomainのProviderを利用せず、MySQLに登録済みの
WorkspacePresetKeyからDefinition IDへの対応だけを利用する。

将来ユーザー定義環境を追加する場合は、Presetとは別のUseCaseでWorkspaceDefinitionを作成し、UserまたはChapter固有の情報と
Definition IDとの対応を保存する。供給元ごとの入力形式を共通化せず、WorkspaceDefinitionの保存後は同じDefinition Repository、
WorkspaceSession、およびRuntimeの契約を利用する。

### desired stateとobserved state

WorkspaceDefinitionとWorkspaceSessionをMySQLへ永続化する。WorkspaceSessionはWorkspaceSession ID、作成時に解決した
WorkspaceDefinitionのDefinition ID、および有効期限を保持する。WorkspacePresetKeyからDefinition IDへの対応はWorkspace作成時の
Definition選択にだけ使用し、作成済みWorkspaceSessionはDefinition IDからWorkspaceDefinitionを直接解決する。

有効期限内のWorkspaceSessionがMySQLに存在する場合は、対応するWorkspaceDefinitionの実行環境を存在させるdesired stateとする。
WorkspaceSessionが存在しない場合、または有効期限を過ぎた場合は、その実行環境を存在させないdesired stateとする。
WorkspaceDefinitionとWorkspaceSessionを、作成、再適用、削除へ収束させるdesired stateの正とする。
k3s上に存在するリソースをobserved stateの正とし、Podなどの実行状態をMySQLへ状態の正として複製しない。最終試行時刻や
エラーなどを運用情報として保存する場合も、実行状態の判断にはk3sから取得したobserved stateを使用する。

WorkspaceComponentの`image`がTagを含む場合、同じ参照からRegistryが異なるImageを返す可能性を許容する。
WorkspaceDefinitionが固定するのはOCI Imageの参照文字列までとし、実際に展開されたImage IDやDigestはk3sのobserved stateとして扱う。

WorkspaceDefinitionまたはWorkspaceSessionをk3sリソース、Label、Annotation、リソース名から復元しない。k3s Metadataは、
MySQL上のdesired stateと実行中リソースを識別および照合するためだけに使用する。

Workspaceの一時ファイルなど、実行環境内の利用者データを永続化して再開する機能は引き続きv0.0.1の対象外とする。

### Jobによる適用

複数のKubernetesリソースを適用する処理は、常駐Controllerではなく、一回実行して終了するJobから行う。APIから呼び出された
Applicationは、MySQL実装のResolverを通してPresetKeyに対応するDefinition IDを解決し、そのIDを持つWorkspaceSessionをMySQLのTransactionで保存して
Commitした後、WorkspaceSession IDを指定してApply Jobの起動を要求する。JobへWorkspaceDefinition、Preset、Manifestを受け渡さない。

Apply JobはInbound AdapterとしてApplicationの適用UseCaseを呼び出す。適用UseCaseはWorkspaceSession IDからMySQL上の
WorkspaceSessionと、Sessionが直接参照するWorkspaceDefinitionを取得し、Infrastructure非依存のPortを通してk3sへ収束を要求する。
WorkspaceSessionが存在しない場合は、WorkspaceSession IDに対応するk3sリソースの削除へ収束させる。

Kubernetes Infrastructureは、WorkspaceDefinitionとWorkspaceSessionから期待するリソース集合と適用順序を決定的に生成する。
リソースごとの論理キーとWorkspaceSession IDから名前を決定し、k3sから取得したobserved stateとの差分に応じて、存在する
リソースの維持、不足リソースの作成、更新、再作成、または不要リソースの削除を行う。

複数リソースの適用をTransactionとして扱わず、途中失敗時に適用済みリソースをRollbackしない。同じJobまたは後続Jobが、
MySQLから同じdesired stateを読み直し、k3sを再観測してリソース単位に再試行する。手続き的な適用済みStepを状態の正として
MySQLへ保存しない。

Job起動要求の失敗やJobのRetry上限到達後にもdesired stateを失わない。未収束のWorkspaceを検出して同じ適用UseCaseを再実行する
定期Jobを用意する。即時Jobと定期Jobが重複しても結果が変わらない契約とし、同じWorkspaceSessionを同時に操作する場合の
排他方式と具体的な実行間隔は後続Issueで決定する。

明示的な終了ではWorkspaceSessionをMySQLから削除した後にJobを起動する。期限切れはMySQLに保存した`expires_at`から判定する。
いずれもMySQL上のdesired stateを先に確定し、同じJob実行方式でk3s上のリソース削除へ収束させる。定期Jobはk3s上の
WorkspaceSession IDとMySQL上のWorkspaceSessionを照合し、不在または期限切れのWorkspaceに対応するリソースも削除する。

### Kustomizeとの関係

Workspace Runtimeのリソース生成にKustomizeを使用しない。Kubernetes InfrastructureがDomainのWorkspaceDefinitionから
Kubernetes Clientの型へ直接変換する。生成処理とk3s APIを操作する処理を分離し、WorkspaceDefinitionの値とManifestの値を
二重管理しない。

同じWorkspaceDefinitionとWorkspaceSession、および同じInfrastructure Policyからは、同じ論理リソース集合を生成する。
Definitionが所有する値を変更するときは新しいDefinitionを作成する。共通のKubernetes固有Policyを変更した場合は、既存Sessionも
新しいPolicyへ収束し得ることを許容する。`image`にTagを使用する場合、同じ論理リソース集合であっても実際に展開されるImageが
変わり得ることを許容する。

### レイヤー境界

- Domain: WorkspacePreset、WorkspaceDefinition、分離したPreset Key／Definition Catalog、WorkspacePresetProvider、
  WorkspaceComponent、AccessPoint、WorkspaceSessionと不変条件、observed stateの集約規則
- Application: WorkspacePresetProviderが返すシステム提供Presetの初期登録、DefinitionとSessionの永続化順序、Transaction、
  Job起動の調整、desired/observed stateを使った処理調整
- Database Infrastructure: WorkspacePresetから分離したWorkspaceDefinitionとPreset対応、およびWorkspaceSessionの保存と取得
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

同じDefinitionを複数Sessionへ重複して保存し、Definition単位で参照と保持を管理できない。WorkspaceSessionは
Definition IDを保持し、独立して保存したDefinitionを直接解決する。

### Definition IDとrevisionを使用する

同じIDのDefinitionを更新し、SessionがIDとrevisionを参照する案。Definition自体を不変とし、変更ごとに新しいIDを
発行する方が、同じIDで異なる構成が解決される可能性を排除できるため採用しない。

## 影響

- WorkspaceDefinition、WorkspacePresetKeyとの対応、およびWorkspaceSession用のTable、Repository、Migrationが必要になる
- APIはWorkspaceSessionの保存とk3s操作を1つのTransactionにせず、desired stateを先にCommitする必要がある
- Workspace作成APIは、k3sへの適用完了ではなく、Job起動要求までを扱う非同期処理になる
- Jobの重複実行、途中失敗、および不明な実行結果を前提に、適用処理をリソース単位で冪等にする必要がある
- k3s Metadataの欠落や不一致を検出する必要があるが、DefinitionまたはSessionの復元元にはしない
- OCI ImageをTagで参照する場合、同じWorkspaceDefinitionから異なるImageが展開され得る
- Preset追加時は、DomainのPreset Key CatalogとDefinition Catalogへそれぞれ追加し、WorkspacePresetProviderで対応付ける必要がある
- WorkspacePresetProviderでDefinitionの不変条件、OCI Image参照、およびPresetKeyとの対応を検証する必要がある
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
