# 0006: k3sのNamespaceをサービス用とWorkspace用に分離する

## 背景

Niora自身と、利用者が起動するWorkspaceを同じk3sクラスタ上で稼働させる。

Niora自身を構成するフロントエンド、Niora API、データベースは、互いに連携するサービスである。一方、Workspaceは教科書の内容を試すために利用者が操作する実行環境であり、Nioraの基盤や他のWorkspaceへアクセスさせてはならない。

WorkspaceごとにNamespaceを作成すると分離と削除は分かりやすくなるが、Workspaceの起動と終了のたびにNamespaceとNamespace単位の設定を管理する必要がある。現時点では利用者が存在せず、まずは小さな開発・運用コストでWorkspaceの起動と接続を実現することを優先する。

## 決定

NioraとWorkspaceを、次の2つのNamespaceに配置する。

| Namespace | 配置するもの |
| --- | --- |
| `ns-niora-service` | フロントエンド、Niora API、MySQL |
| `ns-niora-workspaces` | Niora APIが起動するすべてのWorkspace |

すべてのWorkspaceは`ns-niora-workspaces`を共有する。WorkspaceのリソースにはWorkspaceを一意に識別できるLabelを付与し、Labelを利用してNetworkPolicyの適用対象を識別する。

通信方針を次のように定める。

- Workspace間の通信は禁止する
- 同じWorkspaceに属するPod間の通信は許可する
- `ns-niora-service`からWorkspaceへのInbound通信を許可する
- Workspaceへの利用者からの直接通信は許可せず、Niora APIを経由させる
- WorkspaceからインターネットへのOutbound通信は原則として許可する
- WorkspaceからNiora API、MySQL、k3s API、クラスタノードなど、Nioraの基盤へのOutbound通信は禁止する
- 名前解決に必要なDNS通信は、基盤への通信禁止の例外として必要最小限で許可する

NetworkPolicyは、最初にWorkspaceのIngressとEgressを既定で拒否し、必要な通信だけを追加で許可する方針で構成する。具体的なLabel、Pod Selector、Namespace Selector、許可・除外するCIDRは、採用するk3sのCNI、Pod CIDR、Service CIDR、Node CIDRを確認した上でデプロイ設計に定義する。

標準のNetworkPolicyはドメイン名を宛先として拒否できない。そのため、Niora APIを将来パブリックなIPアドレスで公開した場合、Workspaceからその公開経路を通じてNiora APIへ到達できる可能性がある。この経路も禁止する必要が生じた場合は、公開IPアドレスの除外、Egress Gateway、Proxy、またはCNI固有の機能を別途検討する。

CPUとメモリのRequest、LimitおよびResourceQuotaは、現時点では定めない。利用者の増加、リソース競合、意図しないリソース消費、またはコスト上の問題が確認された時点で再検討する。

## 代替案

### WorkspaceごとにNamespaceを作成する

Workspace単位でNamespaceを作成し、Workspaceの終了時にNamespaceごと削除する案。

分離、Quotaの適用、リソースの一括削除が分かりやすくなる。一方、現時点ではNamespaceの作成・削除、ポリシーの複製、状態管理に必要な実装と運用の負担が利点を上回ると判断したため採用しない。

### NioraとWorkspaceで同じNamespaceを共有する

すべてのコンポーネントを1つのNamespaceへ配置する案。

構成は単純になるが、Nioraの基盤と利用者が操作するWorkspaceの境界が曖昧になり、誤設定時の影響範囲が大きくなるため採用しない。

### WorkspaceからのOutbound通信をすべて禁止する

Workspaceからクラスタ外への通信も含めて禁止する案。

基盤の保護は単純になるが、パッケージ取得や外部サービスへの接続を伴う学習を妨げるため採用しない。

## 影響

- Workspaceの作成・削除処理は、NamespaceではなくLabelとNioraが保持するリソース識別子を使って対象リソースを特定する必要がある
- Labelの欠落や誤りが通信制御と削除処理に影響するため、Niora APIがLabelを一貫して付与し、利用者から変更できないようにする必要がある
- Workspaceごとに共通Labelを選択するNetworkPolicyを作成し、同じWorkspaceのPod間通信だけを許可する必要がある
- 共有Namespace内のNetworkPolicyは追加的に適用されるため、新しい許可ルールによってWorkspace間通信を誤って許可しないように検証が必要になる
- NetworkPolicyを実際に強制できるCNIを使用し、通信テストによって拒否・許可の両方を確認する必要がある
- Namespaceを共有するため、Workspace単位のResourceQuotaは利用できない。必要になった場合は、別の制御方法またはWorkspace単位のNamespaceへの移行を検討する
- CPUとメモリを制限しない期間は、1つのWorkspaceがクラスタ全体のリソースを圧迫するリスクを受け入れる

## 参考

- [Kubernetes: Multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
- [Kubernetes: Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes: Resource Quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
