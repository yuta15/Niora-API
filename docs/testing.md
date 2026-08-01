# テスト方針

Nioraで、何をどの粒度でテストするかを定めます。テストツールの設定は`pyproject.toml`で管理します。

## 基本方針

- すべての組み合わせや実装行を網羅することを目的にせず、障害時の影響が大きい振る舞いを優先する
- 実装内部ではなく、外部から観測できる振る舞いと契約をテストする
- 同じ条件で繰り返し実行でき、実行順序に依存しないテストにする
- 不具合を修正する場合は、不具合を再現して修正後の振る舞いを保証するテストを追加する
- カバレッジは未検証箇所を探すために利用し、カバレッジ率そのものを目標にしない

## 優先する対象

次の対象を優先してテストします。

- ドメインルールと状態遷移
- セキュリティと権限の境界
- Workspaceの起動、状態確認、接続、削除
- 複数リソースを操作する処理の冪等性と途中失敗時の後始末
- Workspaceを構成するPod群からWorkspace状態への変換
- MySQLとk3sのAdapterが提供する契約
- 期限切れWorkspaceの判定と削除
- WebSocket切断時や外部サービス障害時の振る舞い

単純な値の受け渡し、フレームワークやライブラリ自体の動作、実装の非公開部分は原則としてテスト対象にしません。

## テストレベル

### Domainテスト

ドメインルールの文脈でテストを作成します。クラスやメソッドの実装確認ではなく、業務上成立する条件、拒否する条件、状態の変化を表現します。

Domainテストからデータベース、k3s、Webフレームワークへアクセスしません。

### Applicationテスト

外部Portを呼び出すだけの薄いユースケースには、Application単体のテストを作成しません。APIから外部サービスまでを通したE2Eテストで確認します。

ただし、次のいずれかを含むユースケースは、E2Eだけに依存せずApplicationテストを作成します。

- 重要な条件分岐
- 複数のPortをまたぐオーケストレーション
- 冪等性の制御
- 途中失敗時の補償処理や後始末
- トランザクション境界
- セキュリティまたは権限に関する判断

この場合はApplicationが定義するPortのFakeを使用し、ユースケース固有の判断だけを検証します。

### Integrationテスト

Infrastructure Adapterは、Adapterが接続する外部サービスを基準にテストを分けます。

- MySQL Adapterは、デプロイ対象と同じ系列の実際のMySQLへ接続する
- k3s Adapterは、実際のKubernetes APIへ接続する
- 外部サービスのClientをMockして、Clientの呼び出し方だけを確認するテストで代替しない
- Adapterが外部サービスのデータとDomain/Applicationの型を正しく変換できることを確認する
- 外部サービスのエラーを、Applicationが扱うエラーへ正しく変換できることを確認する

テストデータとk3sリソースはテストごとに分離し、成功・失敗にかかわらず後始末します。外部インターネット上の不特定なサービスには依存せず、管理できるテスト用サービスを使用します。

### E2Eテスト

利用者にとって重要な操作の流れを、APIからMySQL、k3s、Workspaceまで通して検証します。E2Eですべての入力パターンを網羅せず、代表的な正常系と影響の大きい異常系に限定します。

少なくとも次の流れを対象にします。

- Workspaceを起動し、状態を確認して削除できる
- WebSocketから対象Podへ`exec`で接続できる
- WebSocketを切断してもWorkspaceが維持され、再接続できる
- 期限切れWorkspaceが削除される
- Workspace間の通信が拒否され、同じWorkspace内の必要な通信が許可される
- WorkspaceからNioraの基盤へアクセスできず、許可された外部通信は利用できる

NetworkPolicyとRBACはMockでは保証せず、実際のk3s環境で検証します。

## Fixture

- Fixtureは、そのFixtureを利用するテスト群に最も近い`conftest.py`へ定義する
- 複数の`conftest.py`配下から利用されるFixtureは、共通の親ディレクトリにある`conftest.py`へ移動する
- `conftest.py`からFixtureを直接importしない
- ルートの`tests/conftest.py`には、すべてのモジュールで本当に共有するFixtureだけを置く
- FixtureのScopeは必要最小限にし、共有によってテスト間で状態が漏れないようにする
- 外部リソースを作成するFixtureは、テスト失敗時にも削除されるように後始末を実装する
- `autouse` Fixtureは、すべての対象テストに必要な不変条件がある場合に限って使用する

Fixture名は生成方法ではなく、テストから見た役割を表す名前にします。

## パラメータ化

準備、操作、期待結果が同じで、入力値と期待値だけが異なるテストには`pytest.mark.parametrize`を使用します。

シナリオの意味、事前条件、操作、確認内容が異なる場合は、無理にパラメータ化せず別のテストとして記述します。失敗時にどのドメインルールが壊れたか分かる粒度を優先します。

## 再現性と分離

- 現在時刻に依存する処理にはClockを注入し、期限を待つための`sleep`を使用しない
- Workspace IDなどの識別子はテストから制御できるようにする
- WebSocketや外部サービスを待つ処理にはTimeoutを設ける
- テストの成否を実行順序や別テストのデータへ依存させない
- MySQLのスキーマとk3sのバージョンは、デプロイ対象と互換性のあるバージョンへ固定する

## ディレクトリ構成

```text
tests/
├── textbook/
│   ├── domain/
│   ├── application/
│   └── integration/
│       └── mysql/
│           └── conftest.py
├── workspace/
│   ├── domain/
│   ├── application/
│   └── integration/
│       ├── mysql/
│       │   └── conftest.py
│       └── k3s/
│           └── conftest.py
├── auth/
└── e2e/
    └── conftest.py
```

`src/<module>`と`tests/<module>`を対応させ、Domain、Application、Integrationのテストをモジュール単位で
まとめます。モジュール横断のシナリオだけを`tests/e2e`へ配置します。存在しないテストレベルのディレクトリを
あらかじめ作成する必要はありません。

## Marker

- 外部サービスを使用するテストに`integration`を付ける
- Niora全体を通して検証するテストに`e2e`を付ける
- Domainテストと外部サービスを使用しないApplicationテストにはMarkerを付けない

```bash
# 外部サービスを使用しないテスト
uv run pytest -m "not integration and not e2e"

# Integrationテスト
uv run pytest -m integration

# E2Eテスト
uv run pytest -m e2e

# すべてのテスト
uv run pytest
```
