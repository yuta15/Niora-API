# Niora API

NioraのバックエンドAPIです。

> 現在はv0.0.1の開発初期段階です。API仕様やアプリケーション構成は今後追加します。

## セットアップ

### 必要な環境

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

### 依存関係のインストール

```bash
uv sync
```

### pre-commitの有効化

```bash
uv run pre-commit install
```

設定後は、コミット時にRuff、mypy、ファイル形式などのチェックが実行されます。

## 開発コマンド

### テスト

```bash
uv run pytest
```

カバレッジを計測する場合：

```bash
uv run pytest --cov=src --cov-branch --cov-report=term-missing
```

> 現在はテスト未作成のため、テスト追加後に利用できます。

### Lint

```bash
uv run ruff check .
```

自動修正する場合：

```bash
uv run ruff check . --fix
```

### Format

```bash
uv run ruff format .
```

フォーマット差分のみ確認する場合：

```bash
uv run ruff format --check .
```

### 型チェック

```bash
uv run mypy .
```

### pre-commit

すべてのファイルをチェックする場合：

```bash
uv run pre-commit run --all-files
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
