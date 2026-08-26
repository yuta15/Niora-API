# 0011: Workspaceリソースのライフサイクルを順序付きStepで構成する

## 背景

WorkspaceSessionに対応する実行環境は、PodだけでなくService、NetworkPolicyなど複数のk3sリソースで構成される。
これらのリソース間の依存関係と、必要な作成順序および削除順序はWorkspacePresetKeyによって異なる可能性がある。

すべてのWorkspaceSessionは`ns-niora-workspaces`を共有するため、WorkspaceSessionの終了時にNamespace全体を削除することは
できない。共通Labelで対象リソースを特定し、WorkspaceSessionごとに必要なリソースだけを削除する必要がある。

プリセットごとに作成処理と削除処理を1つの大きなStrategyとして実装すると、Pod、Service、NetworkPolicyなどに共通する処理を
再利用しにくくなる。一方、作成順序の単純な逆順が適切な削除順序になるとは限らず、作成と削除を同じStepの対として扱うと、
ライフサイクルごとの条件や待機処理を表現しにくい。

## 決定

Workspace Adapterのk3s実装では、WorkspacePresetKeyから`WorkspaceResourcePlan`を解決し、Planに定義された順序でStepを
実行する。Planの解決と実行はWorkspace Adapter内部の技術的な責務とし、Domain ModelおよびApplicationの公開Portには
露出させない。

`WorkspaceResourcePlan`は、次の独立したStep列を持つ。

- 作成時に順番に実行する`WorkspaceProvisioningStep`の列
- 削除時に順番に実行する`WorkspaceDeletionStep`の列

Workspace Adapterは、作成時には`provisioning_steps`を、削除時には`deletion_steps`を先頭から順に実行する。
作成と削除では依存関係、失敗時の扱い、待機条件が異なるため、同じStepに`create`と`delete`を持たせず、別の契約とする。
個々のStepはPod、Service、NetworkPolicyなどのリソース操作や、必要な状態になるまでの待機を担当できる。

Applicationから見た実行環境の操作は、引き続き次の粒度とする。

- WorkspaceSessionを渡して実行環境の作成を要求する
- WorkspaceSessionのIDを渡して実行環境の削除を要求する

ApplicationはStep、Plan、k3sリソースの種類、実行順序を認識しない。

### 作成

作成処理は、WorkspaceSessionが持つWorkspacePresetKeyからPlanを解決し、`provisioning_steps`を順番に実行する。同じ
WorkspaceSessionのIDによる再試行と、作成途中のリソースが存在する場合の後始末は、
[ADR 0010](0010-store-workspace-session-metadata-in-k3s.md)の方針に従う。Planはk3s APIをまたぐTransactionや、実行済みStepの
自動的なRollbackを提供しない。

### 削除

削除処理は、WorkspaceSessionのIDに対応するk3sリソースからWorkspacePresetKeyを取得し、そのPresetのPlanを解決して
`deletion_steps`を順番に実行する。

- 削除対象が存在しないStepは成功として扱う
- Stepが失敗した場合は後続のStepを実行せず、失敗として返す
- 実行済みの削除をRollbackしない
- 再試行時はPlanの先頭から実行し、残っているリソースの削除を継続する
- 後続の削除前に実際の削除完了が必要な場合は、Planへ待機Stepを明示的に含める

必要なすべての削除要求をk3s APIが受理した時点で、Workspace Adapterの削除処理を成功とする。削除したリソースがk3sから
完全に消失するまでを、削除ユースケースの完了条件とはしない。ただし、Planに含めた待機Stepは後続Stepの前提条件として
完了する必要がある。

WorkspaceSessionが存在する間は、そのWorkspacePresetKeyに対応するPlanを作成時と整合する内容で解決できる必要がある。
プリセットの構成を互換性なく変更するときは新しいWorkspacePresetKeyを使用し、既存のPlanは対応するWorkspaceSessionを
削除できる期間保持する。

## 代替案

### プリセットごとに単一のStrategyを実装する

WorkspacePresetKeyごとに作成と削除の全処理を持つStrategyを用意する案。

プリセット固有の順序は表現できるが、同じリソース操作を複数のStrategyへ重複して実装しやすい。小さなStepを組み合わせる
ことで、共通処理を再利用しながらプリセットごとの違いを順序として表現できるため採用しない。

### 作成用Stepを逆順に実行して削除する

作成Stepに作成と削除の両方を持たせ、削除時は作成時の逆順に実行する案。

削除時だけ必要な待機や、作成順序の逆順とは異なる削除順序を表現しにくい。作成と削除の契約を独立させ、Planでそれぞれの
順序を明示する。

### WorkspaceSessionごとにNamespaceを作成して削除する

WorkspaceSessionごとにNamespaceを分離し、終了時にNamespace全体を削除する案。

現在はすべてのWorkspaceSessionが`ns-niora-workspaces`を共有する構成であり、Namespace単位の分離と管理コストを
導入しないため採用しない。

### Helmまたはk3s側の仕組みだけで順序を制御する

HelmのReleaseやHook、KubernetesのOwnerReferenceなどへライフサイクル管理を委ねる案。

デプロイ単位の管理や連鎖削除には利用できるが、プリセットごとに異なる任意の順序、待機、再試行を表すには追加の管理が
必要になる。v0.0.1ではWorkspace Adapter内のPlanで明示的に制御し、プリセットと運用の複雑さが増した時点で再評価する。

## 影響

- Workspace Adapterのk3s実装には、WorkspacePresetKeyからPlanを解決するResolverが必要になる
- リソース操作を小さなStepとして再利用し、プリセットごとの差をStepの組み合わせと順序で表現できる
- 作成と削除の順序を独立して変更できる
- 削除の再試行では、各Stepが対象リソースの不在を正常として扱う必要がある
- Planの途中で失敗すると一部のリソースだけが作成または削除された状態になり得るため、再試行を前提とした実装とテストが必要になる
- 待機Stepを含むPlanでは削除処理に時間がかかる可能性があるが、必要のないPresetへ一律の待機を課さずに済む
- 使用中のWorkspacePresetKeyに対応するPlanを削除または互換性なく変更できない
- 将来Helmや専用Controllerへ移行する場合も、ApplicationとDomainの契約を変更せずAdapter内部を置き換えられる

## 関連ドキュメント

- [アーキテクチャ](../architecture.md)
- [ADR 0006: k3sのNamespaceをサービス用とWorkspace用に分離する](0006-share-k3s-workspace-namespace.md)
- [ADR 0007: Workspaceを1つ以上のPodで構成しk3sを状態の正とする](0007-run-workspaces-as-pods.md)
- [ADR 0009: Workspaceの業務責務と実行環境の技術責務を分離する](0009-separate-workspace-domain-and-runtime-adapters.md)
- [ADR 0010: WorkspaceSessionの情報をk3sリソースに保持する](0010-store-workspace-session-metadata-in-k3s.md)
