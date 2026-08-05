# 用語集

| 用語 | 英語名 | 説明 |
| --- | --- | --- |
| 教科書 | `Textbook` | 学習者へ提供する教材。複数の章で構成する |
| 章 | `Chapter` | 教科書を構成する学習単位。学習内容と対応するWorkspacePresetKeyを持つ |
| ワークスペースプリセットキー | `WorkspacePresetKey` | Nioraが用意した実行環境のプリセットを識別する不変かつ不透明なキー |
| ワークスペースセッション | `WorkspaceSession` | WorkspacePresetKeyで選択したプリセットから開始され、明示的な終了または有効期限まで利用できる学習環境の利用単位 |
| ワークスペース | `Workspace` | WorkspaceSessionに対応して実行基盤上に構築された、操作可能な学習環境 |
| 接続トークン | `ConnectionToken` | 特定のWorkspaceSessionへの接続だけを許可する、有効期限の短い認証情報 |
