# 0007: Workspaceを1つ以上のPodで構成しk3sを状態の正とする

## 背景

v0.0.1では、Workspaceのスケーリングや高可用性を必要としない。一方、将来はUbuntuだけでなく、データベースや各種サービスを組み合わせたWorkspaceを扱う可能性がある。

Workspaceの実行状態をNioraのデータベースにも保存すると、データベース上の状態とk3s上の実際の状態が食い違う可能性がある。また、接続のためにSSHサーバーと認証情報をWorkspace内へ用意すると、実装と管理の対象が増える。

Workspaceには有効期限があり、利用者からの操作がなくても期限切れのWorkspaceを削除する必要がある。

## 決定

### Workspaceの実体

1つのWorkspaceを、`ns-niora-workspaces`内の1つ以上のPodで構成する。Podの種類と数はWorkspaceDefinitionで定義し、実行中に自動でスケールさせない。DeploymentなどのPodを複製・再作成するControllerは使用せず、Niora APIが必要なPodを直接作成する。

Podに加えて、WorkspaceDefinitionに応じてService、NetworkPolicyなど、Workspaceの実行に必要なリソースを作成する。すべてのリソースにWorkspaceを一意に識別する共通のLabelを付与し、各PodにはWorkspace内での役割を識別するLabelも付与する。

Ubuntuへ`exec`で接続するだけのWorkspaceにはServiceを必要としない。Serviceは、Workspace内のサービスへネットワーク接続する必要がある場合にだけ作成する。

Workspace IDからk3sのリソース名を決定できるようにし、同じ起動要求が再試行されてもWorkspaceが重複しないようにする。リソースの作成に途中で失敗した場合は、WorkspaceのLabelを使って作成済みリソースを削除する。

### 状態管理

k3s上のリソースをWorkspaceの実行状態の正とする。

- NioraのデータベースにはWorkspaceの実行状態を保存しない
- 状態確認のたびにNiora APIがk3s APIからWorkspaceに属するすべてのPodの状態を取得する
- WorkspaceDefinitionで必須とされたPod群の状態を集約し、Nioraのドメインで使用するWorkspace状態へ変換する
- WorkspaceのID、有効期限、WorkspaceDefinitionとの対応に必要な実行時情報は、k3sリソースのLabelまたはAnnotationとして保持する

Workspaceのリソース削除後は実行状態と履歴を保持しない。そのため、削除済み、期限切れ、または初めから存在しないWorkspaceを、状態情報だけから区別することは保証しない。

Deploymentを使用しないため、Node障害などでWorkspaceを構成するPodが失われても自動で新しいPodを作成しない。可用性よりも構成と実装の単純さを優先し、この制約を受け入れる。

### 有効期限と削除

Workspaceの有効期限をk3sリソースのAnnotationへ記録する。

`ns-niora-service`に期限切れ削除用のCronJobを1つ配置する。CronJobが定期的にJobを起動し、Jobは`ns-niora-workspaces`のWorkspaceを走査して、現在時刻を過ぎたWorkspaceのPod、Service、NetworkPolicyなどを共通Labelに基づいて削除する。

CronJobが同じ処理を複数回実行しても結果が変わらないように、削除処理を冪等にする。Jobの同時実行は許可しない。具体的な実行間隔と、完了したJobの保持期間はデプロイ設計で決定する。

利用者が明示的にWorkspaceを削除する場合も、期限切れ削除と同じ削除処理を使用する。v0.0.1ではWorkspaceを再開する機能がないため、停止は独立した状態として扱わず、明示的な終了はWorkspaceの削除として扱う。

### 接続方式

Workspaceへの接続にSSHを使用しない。

ブラウザとNiora APIの間をWebSocketで接続し、Niora APIがk3s APIのPod `exec`を使用してWorkspace内に対話シェルを起動する。WorkspaceDefinitionは、`exec`の接続対象となるPodとContainerを識別できる情報を持つ。標準入力、標準出力、標準エラー出力および端末サイズの変更をNiora APIが中継する。

WebSocketまたは`exec`セッションが切断されてもWorkspaceを構成するPod群は削除しない。再接続時は、同じ接続対象のPodに対して新しい`exec`セッションを開始する。Workspaceの削除までは各Pod内のデータを維持するが、削除後のデータ保存と再開は提供しない。

## 代替案

### DeploymentとしてWorkspaceを作成する

Workspaceを構成する各Podをreplica数1のDeploymentとして作成する案。

Pod障害時に再作成できるが、v0.0.1では可用性とスケーリングを重視していない。Podの再作成によって学習中の一時データが失われたまま見かけ上は稼働状態へ戻る可能性もあるため採用しない。

### Workspaceごとに削除用JobまたはCronJobを作成する

Workspaceの起動時に、そのWorkspace専用の削除処理を作成する案。

通常のJobは作成後すぐ実行されるため、期限まで待機させるには実行中のPodを維持する必要がある。WorkspaceごとのCronJobは繰り返し実行されるリソースの作成と削除が必要になる。Workspace数に応じて管理対象が増えるため採用しない。

### Niora APIのプロセス内で期限を監視する

Niora API内のタイマーで期限切れを検出する案。

APIの再起動や複数replica化によって監視の中断や重複実行が発生する。期限切れ削除の実行をk3sのCronJob Controllerへ委ねるため採用しない。

### Workspaceの状態をデータベースへ保存する

Workspaceの状態をNioraのデータベースへ保存し、APIから更新する案。

履歴を残せる一方、k3sの実状態との同期処理が必要になる。v0.0.1では履歴を必要とせず、実状態を都度取得する方が単純なため採用しない。

### SSHでWorkspaceへ接続する

Workspace内でSSHサーバーを起動し、Niora APIまたはブラウザから接続する案。

SSHサーバー、ポート、認証情報の設定と管理が必要になる。k3s APIが提供するPod `exec`で必要な操作を実現できるため採用しない。

## 影響

- Niora APIにはPodの作成、取得、削除と、Podの`exec`を実行する権限が必要になる
- 期限切れ削除Jobには、`ns-niora-workspaces`内の対象リソースを取得・削除する権限が必要になる
- APIと期限切れ削除Jobで同じWorkspace削除ユースケースを利用できる構成にする必要がある
- CronJobは実行時刻どおりに必ず1回だけJobを作るとは限らないため、期限切れの検出には実行間隔分の遅延を許容し、削除処理を冪等にする必要がある
- Workspaceを構成するPodが消失した場合の自動復旧と、Workspace状態の履歴参照は提供できない
- WebSocket切断後もWorkspaceのPod群が残るため、切断をWorkspaceの削除条件にしてはならない
- `exec`接続だけであればWorkspaceへのServiceとPodネットワーク上のInbound通信は不要になる

## 参考

- [Kubernetes: Pods](https://kubernetes.io/docs/concepts/workloads/pods/)
- [Kubernetes: Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Kubernetes: Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes: CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [Kubernetes API: Pod exec](https://kubernetes.io/docs/reference/kubernetes-api/core/pod-v1/#connect-exec)
