# 0017: Workspaceの標準k3sリソースを定義する

## 背景

Workspaceは共有Namespace内で複数のPodから構成される。Workspace間の通信を分離し、Nioraが作成したresourceを一貫して識別するため、標準で作成するresource、名前、およびMetadataを定める必要がある。

## 決定

### 共通resource

`ns-niora-ws` Namespaceと`sa-niora-ws` ServiceAccountはManifestで管理する。`sa-niora-ws`にはRoleまたはClusterRoleBindingを付与せず、ServiceAccount TokenをPodへ自動マウントしない。

Applicationは共通resourceを作成または削除しない。

### Workspace固有resource

ApplicationはWorkspaceSessionごとに次のresourceを作成する。

| resource | 名前 | 用途 |
| --- | --- | --- |
| CiliumNetworkPolicy | `cnp-ws-<session-id>` | Workspaceの通信を分離する |
| Pod | `pod-ws-<session-id>-<component-key-hash>` | WorkspaceComponentを実行する |

WorkspaceDefinitionでネットワーク接続が必要な場合だけServiceを追加する。Serviceは標準resourceに含めない。

### Metadataと命名

Nioraが管理するすべてのresourceに`app.kubernetes.io/managed-by: niora` Labelを付与する。Workspace固有resourceには次のMetadataを付与する。

| 種別 | Key | Value | 対象 |
| --- | --- | --- | --- |
| Label | `session-id` | `<session-id>` | Workspace内のすべてのresource |
| Label | `component-key-hash` | `<component-key-hash>` | Pod |
| Annotation | `expires-at` | RFC3339 UTCの有効期限 | Workspace内のすべてのresource |
| Annotation | `definition-id` | `<definition-id>` | Workspace内のすべてのresource |

`session-id`はUUIDを文字列表現で使用する。`component_key`は64文字以内の小文字英数字とし、`component-key-hash`は`component_key`のSHA-256を小文字Base32（パディングなし）で符号化した52文字の値とする。ハッシュはPod名とLabelに使用する。`session-id`をPod名に含めるため、ハッシュへSession IDを含めない。

### 通信方針

Workspace固有CiliumNetworkPolicyは、`session-id` Labelで同じWorkspaceのPodを選択し、IngressとEgressをdefault denyとする。

- 同じ`session-id`を持つPod間のIngressおよびEgressを許可する
- `ns-niora-service`内のNiora APIからのIngressを許可する。このルールは将来のAPIからWorkspace Podへの直接通信に備える予約であり、現行のPod `exec`接続には使用しない
- CoreDNSへのTCP/UDP 53のEgressを許可する
- `world`へのEgressを許可する
- RFC1918、IPv4 Link-local、IPv6 Unique Local、およびIPv6 Link-local CIDRへのEgressを明示的に拒否する

CiliumのDeny Policyの優先順位により、CIDRへの明示的なDenyは`world`へのAllowに優先する。Ciliumのバージョン、CoreDNSの実ラベル、および既存のcluster-wide policyとの互換性はデプロイ時に確認する。

### 今回の対象外

次は標準resourceの設計・実装に含めない。

- 期限切れWorkspaceを回収するCronJob
- Podの追加security hardening
- PodおよびNamespace単位のResourceQuota、LimitRange、requests、limits
- 予約ルールを利用するNiora APIからWorkspace Podへの直接通信

## 影響

- Workspace Runtime Adapterは、Resourceの作成時に名前とMetadataを決定的に生成する
- NetworkPolicyのselectorには`session-id`を使用し、Workspace間通信を許可しない
- `component_key`の入力制約はCatalogの検証で保証する
- 今回の対象外は独立した後続Issueで設計・実装する

## 関連ドキュメント

- [アーキテクチャ](../architecture.md)
- [ADR 0006: k3sのNamespaceをサービス用とWorkspace用に分離する](0006-share-k3s-workspace-namespace.md)
- [ADR 0016: Workspaceを同期適用し期限切れリソースを回収する](0016-apply-workspace-synchronously-and-clean-up-expired-resources.md)
