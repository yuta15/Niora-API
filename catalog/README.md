# Catalog

このディレクトリには、Gitで管理し、Niora APIの配布Artifactへ同梱する静的Catalogを配置します。

## Workspace system preset

`system/workspace/presets.json` はWorkspace固有のCatalogです。`scripts/seed_system_catalog.py`の
`WorkspacePresetCatalogLoader`がJSONを検証済みの`WorkspacePresetCatalog`へ変換し、
`WorkspacePresetCatalogDiffer`がDatabaseとの差分を分類したうえで、`WorkspacePresetCatalogApplier`がWorkspaceのTable Modelへ直接seedします。

```json
{
  "schema_version": 1,
  "presets": [
    {
      "preset_key": "ws-example",
      "definition": {
        "definition_id": "00000000-0000-0000-0000-000000000000",
        "components": [
          {
            "component_key": "main",
            "image": "ubuntu:24.04",
            "startup_command": ["sleep", "infinity"],
            "terminal_exec": {"command": ["/bin/bash"]}
          }
        ]
      }
    }
  ]
}
```

`startup_command`と`terminal_exec`は省略でき、明示的に`null`を指定することもできます。

初期登録はSchema Migration後、APIまたはJobの起動前に`make seed-system-catalog`で単独実行し、同時には実行しません。
同じ内容の再登録は何も変更せず、
既存値と競合する場合はCatalog全体をrollbackします。Catalogから項目を省略しても、Databaseに登録済みのDefinitionや
Preset対応を削除する意味にはなりません。

Textbook用の開発Catalog投入（`scripts/seed_catalog.py`）とは別の形式・責務であり、共通seed frameworkは設けません。
