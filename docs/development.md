# ローカル開発ガイド

Niora APIをローカルで開発するための詳細な手順とルールを記録します。

基本的なセットアップとコマンドは、トップレベルの[README](../README.md)を参照してください。

## 記載する内容

- ローカルサービスの起動方法
- テストデータの準備
- デバッグ方法
- コーディング規約
- 開発時のトラブルシューティング

## Database設定

`.env.example`を`.env`へコピーし、ローカル専用のDatabase接続情報を設定します。`.env`はGit管理へ追加しません。
設定名と用途は[データベース設計](database.md#設定)を参照してください。

実装では`pydantic-settings`で各設定値を検証し、個別の値からSQLAlchemy Engineで使用する接続URLを組み立てます。接続URL、Password、
設定Objectをデバッグ出力しないでください。

## Database操作

MySQL AdapterとMigrationの実装時に、次の操作をMake targetとして提供します。

| 操作 | Make target | 内部で行う処理 |
| --- | --- | --- |
| 開発・Integrationテスト用MySQLの起動 | `make db-up` | 固定したMySQL 9.7 GA ImageをDocker Composeで起動し、Healthcheckを待つ |
| Migrationの適用 | `make migrate` | `uv run alembic upgrade head` |
| 開発用Catalogの投入 | `make seed-catalog` | `uv run python -m scripts.seed_catalog --textbooks 2 --chapters-per-textbook 5` |
| system Workspace presetの投入 | `make seed-system-catalog` | `uv run python -m scripts.seed_system_catalog` |
| MySQLの停止とVolume削除 | `make db-down` | Docker ComposeのContainerとVolumeを削除する |

Integrationテストの標準実行順序は次のとおりです。

```bash
make db-up
make migrate
uv run pytest -m integration
make db-down
```

テスト失敗時も`make db-down`を実行します。Databaseごとの分離と後始末はpytest Fixtureが担当します。

### 開発用Catalog

`make seed-catalog`は、決定的なUUIDを持つ開発・検証用TextbookとChapterを投入します。Textbook数とTextbookごとの
Chapter数を変更する場合は、次の引数を指定します。

```bash
uv run python -m scripts.seed_catalog --textbooks <Textbook数> --chapters-per-textbook <Chapter数>
```

同じ引数で繰り返し実行しても重複せず、生成対象外の既存行は変更されません。Chapterの位置を別の既存Chapterが
占有している場合は、全体をrollbackして失敗します。生成できるChapterは合計10件までで、
`Textbook数 × TextbookごとのChapter数`が10を超える場合はDatabaseへ接続する前に失敗します。

### system Workspace preset Catalog

`make seed-system-catalog`は、`catalog/system/workspace/presets.json`を読み込み、loaderによる構造検証と
WorkspaceのTable Modelへの直接seedを一つのTransactionで実行します。実行は`make migrate`の後、APIまたはJobの起動前に
単独で行います。別のCatalogを検証・投入する場合は、次のように`--catalog`でPathを指定します。

```bash
uv run python -m scripts.seed_system_catalog --catalog <Catalog Path>
```

同じ定義を再投入した場合はno-opとなり、mappingだけが欠落している場合はmappingを追加します。Definition、Component、Terminal、
Mappingの競合や不完全な状態を検出した場合は、Catalog全体をrollbackします。Catalogから省略した行は削除しません。
この処理は`seed_catalog.py`の開発用Textbook投入とは独立しています。

ComposeのMySQLは、Migration用UserにSchema変更権限を与え、Application用Userには対象Databaseの
`SELECT`、`INSERT`、`UPDATE`、`DELETE`だけを与えます。Application用Userは
`compose/mysql/init/01-create-application-user.sh`によって作成されます。

`docker-entrypoint-initdb.d`の初期化処理は、MySQLのData Volumeが空の場合にだけ実行されます。
User名やPasswordを変更した場合、既存Dataを削除してよいことを確認してから、Volumeを作り直してください。
