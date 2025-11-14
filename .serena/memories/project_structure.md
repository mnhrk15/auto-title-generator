# プロジェクト構造

## ディレクトリ構造

```
auto-title-generator/
├── app/                          # アプリケーションコード
│   ├── __init__.py              # Flaskアプリケーションファクトリー
│   ├── main.py                  # ルーティング、エラーハンドリング、APIエンドポイント
│   ├── generator.py             # AIテンプレート生成ロジック（デュアルSDK対応）
│   ├── scraping.py              # HotPepper Beautyスクレイピング（非同期）
│   ├── featured_keywords.py     # 特集キーワード管理クラス
│   ├── config.py                # 設定管理（環境変数、季節キーワード、文字数制限）
│   ├── data/                    # データファイル
│   │   └── featured_keywords.json  # 特集キーワードデータ
│   ├── static/                  # 静的ファイル
│   │   ├── css/
│   │   │   └── style.css        # スタイルシート（ブルーテーマ）
│   │   └── js/
│   │       └── script.js        # フロントエンドJavaScript
│   └── templates/              # HTMLテンプレート
│       ├── base.html            # ベーステンプレート
│       └── index.html           # メインページ
├── tests/                       # テストファイル
│   ├── conftest.py             # 共通テストフィクスチャ
│   ├── test_generator.py        # AI生成機能テスト
│   ├── test_scraping.py         # スクレイピング機能テスト
│   ├── test_main.py             # Flask APIエンドポイントテスト
│   ├── test_integration.py      # エンドツーエンド統合テスト
│   ├── test_ui.py               # フロントエンドUIテスト（Selenium）
│   ├── test_featured_keywords.py      # 特集キーワード機能ユニットテスト
│   ├── test_featured_integration.py  # 特集キーワード機能統合テスト
│   ├── test_featured_ui.py           # 特集キーワード機能UIテスト
│   └── data/                    # テストデータ
│       ├── test_featured_keywords.json
│       ├── invalid_featured_keywords.json
│       └── malformed.json
├── logs/                        # ログファイル
│   └── app.log                  # アプリケーションログ（ローテーション対応）
├── requirements.txt             # Python依存パッケージリスト
├── run.py                       # 開発サーバー起動スクリプト
├── asgi.py                      # ASGIアダプター（本番環境用）
├── gunicorn.conf.py             # Gunicorn設定ファイル
├── Procfile                     # Renderデプロイ用プロセス定義
├── render.yaml                  # Renderサービス設定
├── runtime.txt                  # Pythonバージョン指定
├── README.md                    # プロジェクト説明書
└── CLAUDE.md                    # Claude Code向け開発ガイド
```

## 主要ファイルの役割

### アプリケーションコード

#### `app/__init__.py`
- Flaskアプリケーションファクトリーパターン
- `create_app()`関数でアプリケーションインスタンスを作成
- ロギング設定
- ブループリント登録

#### `app/main.py`
- メインのルーティングとエラーハンドリング
- APIエンドポイント:
  - `GET /`: メインページ
  - `GET /api/featured-keywords`: 特集キーワード取得API
  - `POST /api/generate`: テンプレート生成API
- 非同期ルート処理
- エラーハンドラー（404, 400, 500）

#### `app/generator.py`
- `TemplateGenerator`クラス
- Google Gemini 2.5 Flashを使用したAI生成
- デュアルSDK構成（新SDK優先、従来SDKフォールバック）
- `thinking_budget=0`設定で高速化
- 非同期生成メソッド: `generate_templates_async()`
- プロンプト生成: `_create_prompt()`

#### `app/scraping.py`
- `HotPepperScraper`クラス
- aiohttpを使用した非同期スクレイピング
- HotPepper Beautyからヘアスタイルタイトルを取得
- レート制限対応
- SSL設定（開発/本番環境で自動切り替え）
- 非同期メソッド: `scrape_titles_async()`

#### `app/featured_keywords.py`
- `FeaturedKeywordsManager`クラス
- 特集キーワードの読み込みと管理
- 性別によるフィルタリング
- キーワード判定機能
- ヘルスチェック機能
- カスタム例外クラス

#### `app/config.py`
- `Config`クラス
- 環境変数の読み込みと管理
- デフォルト値の設定
- 季節キーワード定義
- 文字数制限定義
- スクレイピング設定

### 設定ファイル

#### `run.py`
- 開発サーバー起動スクリプト
- Flask開発サーバーを起動

#### `asgi.py`
- ASGIアダプター
- WsgiToAsgiでFlaskアプリをラップ
- 本番環境で使用

#### `gunicorn.conf.py`
- Gunicorn設定
- ワーカー数: 2
- ワーカークラス: UvicornWorker（非同期対応）
- max_requests: 1000（メモリリーク対策）

#### `requirements.txt`
- Python依存パッケージのリスト
- バージョン固定

### テストファイル

#### `tests/conftest.py`
- 共通テストフィクスチャ
- 環境変数の自動設定
- テストクライアントの作成

#### `tests/test_*.py`
- 各機能のユニットテスト
- 統合テスト
- UIテスト（Selenium）

## データフロー

1. **フロントエンド** (`app/templates/index.html`, `app/static/js/script.js`)
   - ユーザー入力（キーワード、性別、季節）
   - API呼び出し
   - 結果表示

2. **APIエンドポイント** (`app/main.py`)
   - リクエスト受信
   - バリデーション
   - 処理のオーケストレーション

3. **スクレイピング** (`app/scraping.py`)
   - HotPepper Beautyからデータ取得
   - 非同期処理

4. **AI生成** (`app/generator.py`)
   - Gemini 2.5 Flash API呼び出し
   - テンプレート生成
   - デュアルSDK対応

5. **特集キーワード管理** (`app/featured_keywords.py`)
   - キーワード判定
   - フィルタリング
   - プロンプト強化

6. **設定管理** (`app/config.py`)
   - 環境変数読み込み
   - 設定値提供

## 主要な設計パターン

1. **アプリケーションファクトリーパターン**: `create_app()`
2. **非同期コンテキストマネージャー**: セッション管理
3. **エラーバウンダリーパターン**: 包括的なエラーハンドリング
4. **デュアルSDKパターン**: 新SDK優先、フォールバック
5. **設定管理パターン**: 環境変数ベースの設定
