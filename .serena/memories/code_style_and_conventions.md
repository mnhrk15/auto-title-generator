# コードスタイルと規約

## プログラミング言語
- **Python 3.11.8**（推奨バージョン）
- **エンコーディング**: UTF-8

## コードスタイル

### 型ヒント
- 型ヒントを使用（typingモジュール）
- 関数の引数と戻り値に型を明示
- 例: `def function(param: str) -> Dict[str, Any]:`

### Docstring
- クラスと関数にdocstringを記述
- 日本語で記述（プロジェクトが日本語向けのため）
- 例:
```python
def function(param: str) -> Dict:
    """関数の説明"""
```

### 命名規則
- **クラス名**: PascalCase（例: `TemplateGenerator`, `HotPepperScraper`）
- **関数名・変数名**: snake_case（例: `scrape_titles_async`, `api_key`）
- **定数**: UPPER_SNAKE_CASE（例: `GEMINI_API_KEY`, `MAX_TEMPLATES`）
- **プライベートメソッド**: 先頭にアンダースコア（例: `_create_prompt`）

### インポート順序
1. 標準ライブラリ
2. サードパーティライブラリ
3. ローカルモジュール（相対インポート）

例:
```python
import json
import logging
import asyncio
from typing import List, Dict

import aiohttp
from bs4 import BeautifulSoup

from . import config
```

### ログ記録
- `logging.getLogger(__name__)`を使用してモジュールごとにロガーを設定
- ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL
- 日本語メッセージを使用
- 例: `logger.info("TemplateGeneratorが初期化されました")`

### 非同期処理
- 非同期関数には`async def`を使用
- 非同期コンテキストマネージャーには`async with`を使用
- テストでは`@pytest.mark.asyncio`デコレータを使用
- 例:
```python
async def scrape_titles_async(self, keyword: str) -> List[str]:
    async with aiohttp.ClientSession() as session:
        # 処理
```

### エラーハンドリング
- 包括的な例外処理を実装
- カスタム例外クラスを使用（例: `FeaturedKeywordsError`）
- エラーログを記録
- ユーザーフレンドリーなエラーメッセージを返却

### 設定管理
- 環境変数は`app/config.py`で一元管理
- `python-dotenv`を使用して`.env`ファイルから読み込み
- デフォルト値を設定

### コメント
- 日本語で記述
- 複雑なロジックには説明コメントを追加
- TODOコメントは避ける（実装を優先）

## ディレクトリ構造

```
auto-title-generator/
├── app/                    # アプリケーションコード
│   ├── __init__.py        # アプリケーションファクトリー
│   ├── main.py            # ルーティングとエラーハンドリング
│   ├── generator.py       # AI生成ロジック
│   ├── scraping.py        # スクレイピング機能
│   ├── featured_keywords.py # 特集キーワード管理
│   ├── config.py          # 設定管理
│   ├── data/              # データファイル
│   ├── static/            # 静的ファイル（CSS, JS）
│   └── templates/         # HTMLテンプレート
├── tests/                 # テストファイル
├── logs/                  # ログファイル
├── requirements.txt       # 依存パッケージ
├── run.py                 # 開発サーバー起動スクリプト
├── asgi.py                # ASGIアダプター
└── gunicorn.conf.py       # Gunicorn設定
```

## テスト規約

### テストファイル命名
- `test_*.py`形式
- テスト対象モジュール名に対応（例: `test_generator.py`）

### テストクラス命名
- `Test*`形式（例: `TestTemplateGenerator`）

### テスト関数命名
- `test_*`形式（例: `test_generate_templates_async`）

### フィクスチャ
- `conftest.py`で共通フィクスチャを定義
- `@pytest.fixture`デコレータを使用
- 環境変数の自動設定を含む

### 非同期テスト
- `@pytest.mark.asyncio`デコレータを使用
- `pytest --asyncio-mode=auto`で実行

## 禁止事項

### UI/UX変更
- レイアウト、色、フォント、間隔の変更は禁止
- 変更が必要な場合は事前に承認を得る

### 技術スタック変更
- 指定されたバージョンを勝手に変更しない
- 変更が必要な場合は理由を明確にして承認を得る

### 不要なファイル作成
- 明示的に指示されていない限り、新しいファイルを作成しない
- 既存ファイルの編集を優先

### ドキュメント作成
- 明示的に要求されない限り、ドキュメントファイル（*.md）を作成しない

## パフォーマンス考慮事項

### AI生成最適化
- `thinking_budget=0`設定を維持（高速化のため）
- デュアルSDK構成を維持（新SDK優先、フォールバック）

### リソース管理
- 非同期コンテキストマネージャーでセッション管理
- メモリリーク対策（gunicorn max_requests=1000）
- レート制限を設定（スクレイピング間の待機時間）

### 本番環境最適化
- MAX_PAGES=1（本番環境）
- 2ワーカー構成（Render Starterプラン対応）
