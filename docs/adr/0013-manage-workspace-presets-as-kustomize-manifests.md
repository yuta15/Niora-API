# 0013: WorkspacePresetをKustomize ManifestとしてGit管理する

## 背景

Workspace Adapterは、WorkspacePresetKeyからDeployment、Service、NetworkPolicyなど、WorkspaceSessionに必要なk3sリソースの
構成を解決する必要がある。WorkspacePresetKeyは不変かつ不透明なキーであり、DomainとApplicationはPresetの技術的な構成を
認識しない。

Presetの構成をMySQLで管理する場合、リソースDefinitionごとのTable、中間Table、Repository、Migration、およびDefinitionの
Version管理が必要になる。将来、Presetを実行時に登録または編集する場合には有効だが、v0.0.1ではNioraが事前に用意した
Ubuntu環境だけを使用し、利用者がPresetを変更する機能を提供しない。

一方、PresetごとのManifestをPythonコードへ直接記述すると、実行順序や再試行を扱う処理と静的なリソース定義が混在し、
Manifestの変更差分も確認しにくくなる。静的なリソース定義はコードから分離しつつ、Gitで差分、Review、Rollbackを管理できる
方式が必要である。

また、WorkspaceSessionごとにリソース名、Label、Annotationなどを変える必要があるが、生成したManifestを新たな状態の正として
永続化すると、k3s上の実状態との二重管理になる。

## 決定

### Preset Manifestの管理

v0.0.1では、WorkspacePresetを構成するKubernetes ManifestとKustomizationをRepository内でGit管理し、Niora APIの
配布Artifactに含める。WorkspacePresetKeyは、Workspace Adapter内部で対応するKustomization Targetを解決するための
論理的なキーとして使用する。

WorkspacePreset、Deployment Definition、NetworkPolicy Definitionなどを保存するMySQL Tableは作成しない。Chapterは引き続き
WorkspacePresetKeyだけを保持し、PresetのManifest、Kustomization Target、ファイルPathを認識しない。

ManifestにはSecretの実値を含めない。秘密情報が必要なリソースは、Repository外で安全に作成されたKubernetes Secretを参照する。

### SessionごとのManifest生成

Workspace Adapterは、WorkspacePresetKeyに対応するKustomization TargetとWorkspaceSessionの情報から、Session固有の
Manifestを実行時に決定的に生成する。WorkspaceSessionのID、Workspace内での役割、WorkspacePresetKey、有効期限の記録は、
[ADR 0010](0010-store-workspace-session-metadata-in-k3s.md)に従う。

Session固有に生成したKustomizationやManifestは、処理中の一時的なArtifactとして扱い、MySQL、Repository、共有Volumeへ
永続化しない。生成結果はk3s APIへ適用した後に破棄する。Application Processが処理途中で終了した場合は、同じ
WorkspacePresetKeyとWorkspaceSessionの情報から再生成し、既存リソースとの整合性確認と再試行を行う。実行環境の状態は
引き続きk3sを正とする。

### KustomizeとWorkspaceResourcePlanの境界

Kustomizeは、Presetを構成するManifestの合成とSession固有値の反映に使用する。リソースの作成・削除順序、待機条件、
失敗時の扱い、および再試行はKustomizeへ委ねず、[ADR 0011](0011-compose-workspace-resource-lifecycle-steps.md)で決定した
WorkspaceResourcePlanとStepが扱う。

Workspace AdapterはKustomizeで生成したリソースをPlanのStepへ渡し、Stepごとにk3s APIを操作する。Kustomization Targetを
一括適用するだけの処理へ、Planが持つ順序や待機の責務を移さない。

### Presetの互換性

同じWorkspacePresetKeyからは、WorkspaceSessionの存続中に作成時と整合する構成を解決できる状態を維持する。互換性のない
Manifest変更では既存のWorkspacePresetKeyを再利用せず、新しいWorkspacePresetKeyを追加する。旧Presetは、それを参照する
WorkspaceSessionを削除できる期間保持する。

## 代替案

### PresetとリソースDefinitionをMySQLで管理する

Preset、Deployment、NetworkPolicyなどをTableとして管理し、中間Tableで柔軟に組み合わせる案。

Applicationのデプロイと独立してPresetを追加または変更でき、将来の管理機能には適している。一方、v0.0.1では実行時の登録・
編集を行わず、Table、Repository、Migration、Definition間の整合性、および不変なPresetのVersion管理が必要になるため採用しない。
利用者や運用者が実行時にPresetを管理する要件が生じた場合に、Workspace Adapter内部の保存方式として再評価する。

### Presetのリソース定義をPythonコードへ記述する

WorkspacePresetKeyからPython Objectで定義したWorkspaceResourcePlanを直接解決する案。

追加の構成ファイルやレンダリング処理が不要になるが、静的なKubernetesリソース定義とPlanの制御処理が混在し、Manifestの
差分確認やKubernetesの既存Toolによる検証が難しくなるため採用しない。

### Sessionごとに生成したManifestを永続化する

生成済みManifestをMySQL、ファイル、または共有Volumeへ保存し、再試行や削除で再利用する案。

適用した内容をそのまま保持できる一方、k3s上の実状態と生成Manifestの整合性管理、保存先の可用性、Session削除時の後始末が
必要になる。WorkspacePresetKeyとWorkspaceSessionの情報からManifestを決定的に再生成でき、実状態はk3sを正とするため
採用しない。

### Kustomizeへリソースのライフサイクル管理を委ねる

PresetのKustomization Targetを一括で適用および削除し、WorkspaceResourcePlanを使用しない案。

Manifestの合成は簡潔になるが、作成と削除で異なる順序、状態待機、途中失敗、および冪等な再試行を表現できないため採用しない。

## 影響

- WorkspacePresetを保存するTable、Migration、MySQL Repositoryはv0.0.1では作成しない
- Preset ManifestとKustomizationはNiora APIの配布ArtifactのVersionとともに配布される
- Workspace Adapterには、WorkspacePresetKeyからKustomization Targetを解決し、Session固有Manifestを生成する処理が必要になる
- Kustomizeとk3sの対象Versionに対してPresetを検証し、生成されるManifestが有効であることをCIで確認する必要がある
- 登録済みChapterのWorkspacePresetKeyがすべて解決できることをIntegrationテストで確認する必要がある
- Session固有Manifestの生成結果は永続化せず、必要に応じてWorkspacePresetKeyとWorkspaceSessionの情報から再生成する
- 生成Manifestには秘密情報が含まれる可能性があるため、Manifest全文を通常のLogへ出力しない
- 互換性のないPreset変更では新しいWorkspacePresetKeyを追加し、使用中の旧Presetを削除しない運用が必要になる
- 将来Presetを実行時に登録または編集する場合も、DomainとApplicationの契約を変更せず、Workspace Adapter内部の保存方式を
  MySQLなどへ置き換えられる

## 関連ドキュメント

- [アーキテクチャ](../architecture.md)
- [デプロイと運用](../deployment.md)
- [ADR 0001: v0.0.1の対象範囲を定義する](0001-define-version-0.0.1-scope.md)
- [ADR 0007: Workspaceを1つ以上のPodで構成しk3sを状態の正とする](0007-run-workspaces-as-pods.md)
- [ADR 0009: Workspaceの業務責務と実行環境の技術責務を分離する](0009-separate-workspace-domain-and-runtime-adapters.md)
- [ADR 0010: WorkspaceSessionの情報をk3sリソースに保持する](0010-store-workspace-session-metadata-in-k3s.md)
- [ADR 0011: Workspaceリソースのライフサイクルを順序付きStepで構成する](0011-compose-workspace-resource-lifecycle-steps.md)
