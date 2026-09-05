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

設定後は、コミット時にファイル形式の検証に加えて`make check`が実行され、Ruff、mypy、Pyright、
import-linter、外部サービスを使用しないテストが検証されます。

## 開発コマンド

主要な開発コマンドはMakefileから実行します。利用可能なtargetは次のとおりです。

| 操作 | Make target |
| --- | --- |
| 依存関係のインストール | `make install` |
| 依存関係の同期 | `make sync` |
| 開発サーバーの起動 | `make dev` |
| Lint | `make lint` |
| Lintの自動修正 | `make lint-fix` |
| Format | `make format` |
| Formatの確認 | `make format-check` |
| 型チェック（mypy、Pyright） | `make typecheck` |
| アーキテクチャ依存チェック | `make architecture/imports` |
| 外部サービスを使用しないテスト | `make test` |
| すべてのテスト | `make test-all` |
| カバレッジ付きテスト | `make test-cov` |
| 開発用Textbook/Chapterの投入 | `make seed-catalog` |
| pre-commitの有効化 | `make pre-commit-install` |
| pre-commitの全ファイル実行 | `make pre-commit` |
| 変更を加えない総合チェック | `make check` |

コミット前やPull Request作成前には、変更を加えない`make check`を実行してください。

### テスト

```bash
make test
```

開発サーバーを起動する場合：

```bash
make dev
```

起動後は`http://127.0.0.1:8000/docs`でAPIドキュメントを確認できます。

すべてのテスト（Integration、E2Eを含む）を実行する場合：

```bash
make test-all
```

カバレッジを計測する場合：

```bash
make test-cov
```

開発・検証用のTextbookとChapterを投入する場合（事前に`make db-up`と`make migrate`を実行）：

```bash
make seed-catalog
```

件数を指定する場合は、同じCLIを直接実行します。

```bash
uv run python -m scripts.seed_catalog --textbooks 2 --chapters-per-textbook 5
```

生成できるChapterは合計10件までです。`Textbook数 × TextbookごとのChapter数`が10を超える指定は、
Databaseへ接続する前に拒否されます。

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
