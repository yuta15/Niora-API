# Niora API

NioraのバックエンドAPIです。

> 現在はv0.0.1の開発初期段階です。API仕様やアプリケーション構成は今後追加します。

## セットアップ

### 必要な環境

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

### 依存関係のインストール

```bash
make install
```

依存関係だけを同期する場合は`make sync`を使用します。

### pre-commitの有効化

```bash
make pre-commit-install
```

設定後は、コミット時にRuff、mypy、ファイル形式などのチェックが実行されます。

## 開発コマンド

主要な開発コマンドはMakefileから実行します。利用可能なtargetは次のとおりです。

| 操作 | Make target |
| --- | --- |
| 依存関係のインストール | `make install` |
| 依存関係の同期 | `make sync` |
| Lint | `make lint` |
| Lintの自動修正 | `make lint-fix` |
| Format | `make format` |
| Formatの確認 | `make format-check` |
| 型チェック（mypy、Pyright） | `make typecheck` |
| アーキテクチャ依存チェック | `make architecture/imports` |
| 外部サービスを使用しないテスト | `make test` |
| すべてのテスト | `make test-all` |
| カバレッジ付きテスト | `make test-cov` |
| pre-commitの有効化 | `make pre-commit-install` |
| pre-commitの全ファイル実行 | `make pre-commit` |
| 変更を加えない総合チェック | `make check` |

コミット前やPull Request作成前には、変更を加えない`make check`を実行してください。

### テスト

```bash
make test
```

すべてのテスト（Integration、E2Eを含む）を実行する場合：

```bash
make test-all
```

カバレッジを計測する場合：

```bash
make test-cov
```

### 依存関係の追加

実行時依存を追加する場合：

```bash
uv add <package>
```

開発用依存を追加する場合：

```bash
uv add --dev <package>
```

## ドキュメント

設計、API仕様、開発ガイドなどの詳細は[docs](docs/README.md)にまとめます。

プロジェクトで共通して使用する用語は[用語集](docs/glossary/glossary.md)を正とし、コード、API、データベース、ドキュメントで同じ英語名を使用します。新しい用語の追加や既存用語の変更を行う場合は、[用語集の運用ルール](docs/glossary/README.md)に従ってください。
