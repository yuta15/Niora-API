# 0009: Workspaceの業務責務と実行環境の技術責務を分離する

## 背景

Nioraでは、章に対応する学習環境の起動から期限切れ削除までを扱う。これまでWorkspaceDefinitionが、環境の種類と、
Podや接続対象など実行環境の詳細をまとめて表すことを想定していた。

実行環境の詳細は実行基盤と接続方式に依存する。一方、起動した学習環境の識別、有効期限、状態、接続権限、終了条件は、
利用者へ提供する学習体験に関わる。v0.0.1ではNioraが事前に用意した環境だけを使用するため、この範囲に合わせて
Workspaceモジュールの業務責務と技術責務を分離する必要がある。

## 決定

### Workspaceモジュールの責務

`Workspace`モジュールは、章に対応する期限付きの学習環境を開始し、状態確認、接続権限の発行、接続、明示的な終了、
期限切れ削除までのライフサイクルを扱う。Connectionは独立したDomainモジュールとせず、Workspaceへ接続する
ユースケースと、その技術的な実現方式としてWorkspaceモジュール内で扱う。

### Domainの責務

Domainでは、起動してから終了するまでの期限付きの学習環境を`WorkspaceSession`として扱い、次の情報を持つ。

- WorkspaceSessionを一意に識別するID
- 使用する実行環境を示すWorkspacePresetKey
- 利用可能な期限

WorkspacePresetKeyは、Nioraが提供するプリセットを識別する不変かつ不透明なキーとする。実行環境の種類は
WorkspacePresetKeyで、起動済みの実体はWorkspaceSessionのIDで識別する。

Domainでは、WorkspaceSessionの期限切れ、利用者向けのWorkspace状態、接続可否、接続権限、終了条件を扱う。
技術的なConnectionの切断はWorkspaceSessionの終了条件としない。Domainは実行基盤上のリソースや接続プロトコルを
認識しない。

### Applicationの責務

ApplicationはWorkspaceSessionのユースケースを調整し、Domainの判断に基づく実行環境とConnectionの操作をPortから
Adapterへ要求する。ApplicationはWorkspacePresetKeyを渡すが、実行環境の詳細へ変換しない。

### Adapterの責務

Adapterは、次の技術的な責務を扱う。

- WorkspacePresetKeyから技術的な構成を解決し、実行環境を作成する
- WorkspaceSessionのIDと実行環境を関連付け、状態取得と削除を行う
- 実行環境の状態をDomainのWorkspace状態へ変換する
- Connection方式と接続権限の技術的な表現を実装する

プリセットの保存方法、実行環境との関連付け方、接続プロトコルはAdapterの内部詳細とする。Adapterが接続権限を
技術的に検証した後も、接続可否はDomainの規則に基づいてApplicationが判断する。

### WorkspaceDefinitionの扱い

v0.0.1ではWorkspaceDefinitionをDomain Entityとして定義せず、ChapterはWorkspacePresetKeyを参照する。将来、
教材投稿者が実行環境を定義できるようにする場合は、Domain Modelと技術的なプリセットの境界を改めて決定する。

### 実行状態の正

実行環境の存在と状態は、引き続きk3sを正とする。[ADR 0007](0007-run-workspaces-as-pods.md)の決定を維持し、
Nioraのデータベースへ重複する実行状態を保存しない。

## 代替案

### WorkspaceDefinitionへ実行環境の詳細を含める

WorkspaceDefinitionに実行環境の詳細を持たせる案。v0.0.1では利用者が判断または変更する情報ではなく、実行基盤と
接続方式の変更がDomainへ波及するため採用しない。

### WorkspaceをDomainで扱わず、すべてAdapterで処理する

WorkspacePresetKeyを受け取ったAdapterがすべてを処理する案。WorkspaceSessionの期限、状態、接続権限、終了条件まで
外部技術の処理へ混在し、学習環境のライフサイクルを業務規則として表現できないため採用しない。

### Connectionの切断時に実行環境を削除する

ConnectionをWorkspaceの利用単位とし、切断時に実行環境を削除する案。一時的な通信断でも学習中の環境を失い、
再接続できなくなるため採用しない。

## 影響

- WorkspaceのDomainは、WorkspaceSessionのライフサイクルと接続権限に集中できる
- ChapterとWorkspaceモジュールの境界では、WorkspaceDefinitionのIDではなくWorkspacePresetKeyを受け渡す
- Adapterはプリセット解決、実行環境との関連付け、Connection方式に責任を持つ
- 実行基盤やConnection方式を変更しても、WorkspaceSessionの業務規則を維持しやすくなる
- Connection切断後も実行環境が残るため、明示的な終了と期限切れ削除を確実かつ冪等に実行する必要がある
- 教材投稿者が独自の実行環境を定義できるようにする場合は、DomainとAdapterの境界を再評価する必要がある
- [ADR 0004](0004-use-clean-architecture.md)のWorkspaceモジュールの責務を具体化し、WorkspaceDefinitionをDomainで扱う部分を更新する
- [ADR 0007](0007-run-workspaces-as-pods.md)のWorkspaceDefinitionがPod構成と接続対象を持つ決定を、本ADRで置き換える

## 関連ドキュメント

- [要件](../requirements.md)
- [アーキテクチャ](../architecture.md)
- [用語集](../glossary/glossary.md)
- [ADR 0001: v0.0.1の対象範囲を定義する](0001-define-version-0.0.1-scope.md)
- [ADR 0004: ソフトウェア構成にクリーンアーキテクチャを採用する](0004-use-clean-architecture.md)
- [ADR 0007: Workspaceを1つ以上のPodで構成しk3sを状態の正とする](0007-run-workspaces-as-pods.md)
