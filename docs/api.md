# API実装規約

Niora APIにおけるFastAPI Adapterの構成、ルーティング、Schema、依存性注入の規約を定めます。
APIを作成または変更するときは、この規約に従います。

APIのパスや入出力など、利用者へ公開する契約はOpenAPIを正とします。このファイルでは、OpenAPIを生成する
FastAPIコードの実装方法を扱います。

## ディレクトリ構成

APIは`src/api`へ配置し、メジャーバージョン、その配下をドメインモジュール単位で分けます。

```text
src/api/
├── dependencies/
│   ├── textbook.py
│   └── workspace.py
└── v1/
    ├── router.py
    ├── textbook/
    │   ├── router.py
    │   └── schemas.py
    └── workspace/
        ├── router.py
        └── schemas.py
```

- `src/api/dependencies/<domain>.py`は、ドメインごとにApplicationのUseCaseやその他の依存をFastAPIへ提供します
- `src/api/v1/router.py`は、v1に属するすべてのドメインrouterを集約します
- 各ドメインの`router.py`は、ドメインが公開するpath operationを定義します
- 各ドメインの`schemas.py`は、HTTPのRequest SchemaとResponse Schemaを定義します
- `__init__.py`は図から省略しています
- 実装が存在しないドメインのディレクトリやファイルは、先に作成しません

## Router

各ドメインの`router.py`は、モジュールレベルに`router`という名前の`APIRouter`を1つ公開します。
path operationは`@router.get()`、`@router.post()`などのdecoratorで宣言します。

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import provide_list_textbooks
from src.api.v1.textbook.schemas import ListTextbooksResponse
from src.textbook.application.usecases import ListTextbooks


router = APIRouter(tags=["textbooks"])


@router.get("/textbooks", response_model=ListTextbooksResponse)
def list_textbooks(
    use_case: Annotated[ListTextbooks, Depends(provide_list_textbooks)],
) -> ListTextbooksResponse:
    output = use_case.execute()
    return ListTextbooksResponse.from_output(output)
```

次の実装は、動的な経路生成が必要な場合を除いて使用しません。

- `add_api_route()`による通常のpath operation登録
- 依存を渡すことだけを目的としたrouter factory
- 依存を閉じ込めることだけを目的としたhandler factoryやclosure

これらはFastAPIの標準的な宣言方法と依存性注入を隠し、path operationとOpenAPIの定義を追いにくくするためです。

## バージョンRouter

メジャーバージョン直下の`router.py`も、モジュールレベルに`router`を公開します。ドメインrouterは
`include_router()`で集約します。

```python
from fastapi import APIRouter

from src.api.v1.textbook.router import router as textbook_router
from src.api.v1.workspace.router import router as workspace_router


router = APIRouter(prefix="/v1")
router.include_router(textbook_router)
router.include_router(workspace_router)
```

FastAPIアプリケーションは、バージョンrouterだけを`include_router()`します。新しいメジャーバージョンを追加するときは、
既存バージョンのrouterやSchemaを暗黙に変更しません。

## 依存性注入

UseCaseなどpath operationが必要とする依存は、FastAPIの`Depends`で注入します。型情報を維持するため、
`Annotated`を使用します。

- 依存を生成するproviderは`src/api/dependencies/<domain>.py`へドメイン別に配置します
- providerはメジャーバージョン配下へ置かず、複数のAPIバージョンから再利用できる構成にします
- providerでRepositoryなどのOutbound AdapterとUseCaseを組み立てます
- `router.py`は具象Repositoryやデータベース、k3s clientを直接生成しません
- `app.dependency_overrides`はテストで依存を置き換えるために使用し、本番の通常の組み立てには使用しません
- DomainとApplicationは`FastAPI`、`Depends`、Pydantic Schemaへ依存しません

## Path operation

- 同期I/Oまたは同期UseCaseを呼ぶpath operationは`def`で定義します
- `await`が必要な処理を呼ぶpath operationは`async def`で定義します
- FastAPIを使用しているという理由だけで、すべてを`async def`にしません
- HTTP status、path parameter、query parameter、Request bodyはFastAPIの宣言で明示します
- 成功レスポンスは`response_model`で明示します
- Applicationから返された未検出や競合などの結果は、API Adapterで適切なHTTPエラーへ変換します

## Schema

HTTPのRequest SchemaとResponse SchemaにはPydanticの`BaseModel`を使用し、ドメインごとの`schemas.py`へ配置します。

- Request Schemaは`CreateWorkspaceRequest`のように`Request`を末尾へ付けます
- Response Schemaは`GetTextbookResponse`のように`Response`を末尾へ付けます
- path parameterやquery parameterだけで表現できる入力に、不要なRequest Schemaを作りません
- API SchemaをApplicationのInput、OutputやDomain Entityとして使用しません
- ApplicationのInput、OutputとAPI Schemaの変換はAPI Adapter内で行います
- 単純な変換はpath operationまたはSchemaの`from_output()`などへ置きます
- 業務判断や外部I/OをSchemaの変換処理へ含めません
- 複数箇所で複雑な変換が必要になった場合は、配置を改めて決定してから共通化します

## Routerの集約順序

Routerは次の順序で集約します。

```text
ドメインrouter
    ↓ include_router
メジャーバージョンrouter
    ↓ include_router
FastAPIアプリケーション
```

ドメインrouterをFastAPIアプリケーションへ直接includeせず、必ずメジャーバージョンrouterを経由させます。

## 参考資料

- [FastAPI: Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI: Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
