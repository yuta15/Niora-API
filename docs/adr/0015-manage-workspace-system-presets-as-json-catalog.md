# 0015: Workspace system presetをJSON CatalogとしてGit管理する

## 背景

ADR 0014では、WorkspacePresetKeyとWorkspaceDefinitionを不変なDomain Modelとして扱い、システム提供PresetをDomainの
別々のCatalogで管理することを決定した。Pythonの静的値としてCatalogを保持すると、実行ロジックと構成データが同じ差分に
混在し、配布物に何が含まれるかを確認しにくい。また、将来Presetを追加するたびにDomainへ具体的な識別子を追加することになる。

## 決定

システム提供Workspace presetは、Repository内の`catalog/system/workspace/presets.json`でGit管理し、Niora APIの配布
Artifactへ同梱する。CatalogはWorkspace固有のschemaを持ち、共通seed frameworkやTextbook用の開発Catalogとは統合しない。

`scripts/seed_system_catalog.py`がファイルPathを受け取り、stdlibの`json`で読み込む処理を所有する。
`WorkspacePresetCatalogLoader`がschemaの型、必須・未知フィールド、配列、UUID、argvを構造検証し、
`WorkspacePresetKey`、`WorkspaceComponent`、`WorkspaceDefinition`、`WorkspacePreset`からなる
`WorkspacePresetCatalog`へ変換する。`WorkspacePresetCatalogDiffer`がDatabaseとの差分をinsert・unchangedに分類し、
`WorkspacePresetCatalogApplier`がその計画をTransactionへ適用する。読み込み・検証エラーにはCatalog file、JSON path、および配列indexを含め、
CLIでは組み込み例外の内容をログへ出力する。
Domainは具体的なsystem preset key、definition、対応表、factoryへ依存しない。

初期登録はSchema Migration後、APIまたはJobの起動前に`make seed-system-catalog`で単独実行する。同時実行は行わない。
Alembicのdata migrationやApplication起動時の自動seedには含めず、Textbookの開発データ投入とも別の責務にする。
実行時のPreset解決ではJSONを直接参照せず、MySQLに登録済みの対応を正とする。

登録はCatalog全体を1つのTransactionとして扱う。未登録の値は追加し、同じPreset key、Definition ID、Definition構成の
再登録は何も変更しない。既存値との不一致はCatalog全体をrollbackする。Catalogから項目を省略しても、Databaseに登録済みの
DefinitionまたはPreset対応は削除しない。

## 影響

- Preset追加・変更の構成差分をJSONとしてレビュー、Rollbackできる
- loaderの構造検証により、不正なCatalogをDomainへ渡さない
- 配布ArtifactのRuntime stageにも`catalog`と`scripts`を同梱する必要がある
- `scripts/seed_system_catalog.py`がCatalog読み込みとDatabase seedを所有する
- system Catalogを投入するseed scriptは、loader検証と直接DB投入を同じ冪等契約で実行する

## 関連ドキュメント

- [アーキテクチャ](../architecture.md)
- [ADR 0014: Workspaceのdesired stateを永続化しJobでk3sへ収束させる](0014-persist-workspace-desired-state-and-apply-with-jobs.md)
