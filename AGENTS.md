# AGENTS.md

## Project

Niora APIは、教科書に対応したWorkspaceをk3s上に起動し、ブラウザから操作できる学習環境を提供するバックエンドAPIです。

## Context

作業に必要な情報だけを確認してください。

* 要件：`docs/requirements.md`
* v0.0.1範囲：`docs/adr/0001-define-version-0.0.1-scope.md`
* 用語：`docs/glossary/glossary.md`
* 現在の構成：`docs/architecture.md`
* API規約：`docs/api.md`
* ADR索引：`docs/adr/decisions.md`
* テスト方針：`docs/testing.md`
* 開発コマンド：`README.md`

すべてのドキュメントやADRを一律に読まないでください。
変更対象を特定してから必要なものだけを参照し、ADRは`decisions.md`から関連するものだけを確認します。

## Rules

* `architecture.md`を現在の構成の正とする
* 既存要件・architecture・ADRに反する変更を暗黙に行わない
* v0.0.1対象外機能を依頼なしに追加しない
* API変更は`docs/api.md`、テスト変更は`docs/testing.md`に従う
* ドキュメントは日本語、コード/API/DB上の識別子は用語集の英語名を使う
* 必要以上に変更範囲を広げない
* 最終確認で最低限`make check`を成功させる

### Python import

* 公開クラス・関数・型は責務を持つ最も近い`__init__.py`で再エクスポートし、`__all__`へ明示する
* 利用側は公開元パッケージからimportする
* `__init__.py`内部では相対importを使う
* レイヤー境界を越える再エクスポートや循環importを作らない
* ドキュメントのimport例も公開パスへ揃える

## Agent usage

Solが全体判断と最終確認を担当します。

通常は次の最小構成を選びます。

* `Sol`：質問、調査、設計、軽微な変更
* `Sol → Luna`：設計が明確な通常実装
* `Sol → Terra → Luna`：実装前の設計判断が重要
* `Sol → Luna → Terra`：設計は明確だが独立レビューが必要
* `Sol → Terra → Luna → Terra`：高リスク変更のみ

ファイル数や変更行数だけを理由にTerraを使用しません。

### Terraを実装前に使う条件

次のいずれかに該当する場合：

* architectureやADRの判断が必要
* 複数の妥当な実装方式がある
* 新しい責務・抽象化を導入する
* DB整合性、トランザクション、並行処理に影響する
* 認証・認可・RBAC・NetworkPolicyに影響する
* Kubernetesの構成やライフサイクルを変更する
* 手戻りコストの高い設計判断を伴う

### Terraを実装後に使う条件

次のいずれかに該当する場合：

* セキュリティ境界を変更した
* DB整合性、並行処理、トランザクションを変更した
* architectureまたはADRに関係する変更
* Kubernetesやネットワーク境界を変更した
* 広範囲な挙動変更や大きなリファクタリング
* 利用者がレビューを要求した

## Context transfer

Solだけが必要に応じて広く情報を確認します。

Luna/Terraには原則として次だけを渡します。

* タスク
* 対象範囲
* 守るべき要件・設計制約
* 変更禁止範囲
* 完了条件
* 必要なテスト

ドキュメント、ADR、会話履歴を全文で渡さず、必要な結論だけを要約してください。

サブエージェント自身が追加ドキュメントを読むのは、渡された情報だけでは判断できない場合に限定します。

レビュー結果も全文転送せず、Solが採用した指摘だけをLunaへ渡します。

## Validation

* 実装中は変更箇所に関係する狭いテストを優先する
* 同じ検証を複数エージェントで不要に繰り返さない
* Terraは原則レビューのみ行い、必要な追加検証を指摘する
* Solが最終的に`make check`を確認する
* 成功ログは要約し、失敗時も原因調査に必要な部分だけ扱う

## Security

* `.env`等の秘密情報を含む可能性があるファイルを読まない
* 環境変数は`.env.example`のみ参照する
* `env`、`printenv`、`set`等で環境変数を一括出力しない
* パスワード、Token、秘密鍵、Cookie、認証Headerを出力しない
* セキュリティ境界を明示的な判断なしに弱めない

秘密情報、重大なバグ、セキュリティ問題、要件・architecture・ADR間の矛盾、実行できなかった必須検証を発見した場合は、値そのものを露出せず利用者へ通知してください。
