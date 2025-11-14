# 主要コンポーネントとAPI

## 主要クラス

### TemplateGenerator (`app/generator.py`)
AIテンプレート生成を担当するクラス。

**主要メソッド**:
- `__init__(model_name='gemini-2.5-flash')`: 初期化、デュアルSDK設定
- `generate_templates_async()`: 非同期でテンプレート生成
- `_create_prompt()`: プロンプト生成（特集キーワード対応）
- `_validate_template()`: テンプレート検証（文字数制限）

**特徴**:
- デュアルSDK構成（新SDK優先、従来SDKフォールバック）
- thinking_budget=0設定で高速化
- 特集キーワード対応プロンプト生成

### HotPepperScraper (`app/scraping.py`)
HotPepper Beautyからの非同期スクレイピングを担当するクラス。

**主要メソッド**:
- `__init__()`: 初期化、SSL設定、ヘッダー設定
- `__aenter__()` / `__aexit__()`: 非同期コンテキストマネージャー
- `scrape_titles_async()`: 非同期でタイトルをスクレイピング
- `scrape_titles()`: 同期版（後方互換性）

**特徴**:
- aiohttpを使用した完全非同期処理
- レート制限対応
- 開発/本番環境でSSL設定を自動切り替え

### FeaturedKeywordsManager (`app/featured_keywords.py`)
特集キーワードの管理を担当するクラス。

**主要メソッド**:
- `__init__(json_path)`: 初期化、JSONファイル読み込み
- `load_keywords()`: キーワードの読み込み
- `is_featured_keyword(keyword)`: キーワード判定
- `get_keyword_info(keyword)`: キーワード情報取得
- `get_all_keywords(gender=None)`: 全キーワード取得（性別フィルタリング）
- `is_available()`: 機能の利用可能性チェック
- `reload_keywords()`: キーワードの再読み込み
- `get_health_status()`: ヘルスチェック

**特徴**:
- JSONファイルからのキーワード管理
- 性別によるフィルタリング
- エラーハンドリングとフォールバック

### Config (`app/config.py`)
設定管理を担当するクラス。

**主要設定**:
- `GEMINI_API_KEY`: Gemini APIキー
- `SCRAPING_DELAY_MIN/MAX`: スクレイピングレート制限
- `MAX_PAGES`: スクレイピングページ数制限
- `MAX_TEMPLATES`: 生成テンプレート数制限
- `CHAR_LIMITS`: 各テンプレート要素の文字数制限
- `SEASON_KEYWORDS`: 季節キーワード定義

## APIエンドポイント

### GET `/`
メインページを表示。

### GET `/api/featured-keywords?gender={ladies|mens}`
特集キーワードを取得するAPI。

**パラメータ**:
- `gender` (オプション): `ladies` または `mens` - 性別によるフィルタリング

**レスポンス例**:
```json
{
  "success": true,
  "keywords": [
    {
      "name": "くびれヘア",
      "keyword": "くびれヘア",
      "gender": "ladies"
    }
  ],
  "gender": "ladies",
  "total_keywords": 10,
  "filtered_keywords": 5,
  "health_status": {
    "is_available": true,
    "keywords_count": 10,
    "file_exists": true
  },
  "status": 200
}
```

### POST `/api/generate`
テンプレート生成API。

**リクエストボディ**:
```json
{
  "keyword": "くびれヘア",
  "gender": "ladies",
  "season": "spring",
  "model": "gemini-2.5-flash"
}
```

**レスポンス例**:
```json
{
  "success": true,
  "is_featured": true,
  "keyword_type": "featured",
  "processing_mode": "featured",
  "featured_keyword_info": {
    "name": "くびれヘア",
    "condition": "スタイル名に『くびれヘア』を含めること。"
  },
  "templates": [
    {
      "title": "大人可愛いくびれヘアスタイル",
      "menu": "カット + カラー",
      "comment": "トレンドのくびれヘアで素敵にイメチェン",
      "hashtag": "#くびれヘア #大人可愛い #ヘアスタイル",
      "is_featured": true
    }
  ]
}
```

## 主要関数

### create_app() (`app/__init__.py`)
Flaskアプリケーションファクトリー関数。

**処理内容**:
- Flaskアプリケーションインスタンス作成
- 設定の読み込み
- ロギング設定
- ブループリント登録

### process_template_generation() (`app/main.py`)
テンプレート生成処理をオーケストレートする非同期関数。

**処理フロー**:
1. キーワードの前処理（正規化、複数キーワード検出）
2. 特集キーワード判定（FeaturedKeywordsManager使用）
3. 処理モード決定（featured/standard/fallback）
4. 非同期スクレイピング（HotPepperScraper使用）
5. AI生成（TemplateGenerator使用）
6. テンプレート検証とメタデータ追加
7. 結果返却

**特徴**:
- 複数キーワード対応
- 特集キーワードと通常キーワードの混在処理
- 包括的なログ記録
- エラーハンドリングとフォールバック

## データフロー

1. **フロントエンド** → `/api/generate` (POST)
2. **process_template_generation()** が呼び出される
3. **キーワード判定** → FeaturedKeywordsManager
4. **スクレイピング** → HotPepperScraper.scrape_titles_async()
5. **AI生成** → TemplateGenerator.generate_templates_async()
6. **検証とメタデータ追加**
7. **レスポンス返却** → フロントエンド

## エラーハンドリング

### エラータイプ
- `FeaturedKeywordsError`: 特集キーワード関連の基本エラー
- `FeaturedKeywordsLoadError`: キーワード読み込みエラー
- `FeaturedKeywordsValidationError`: キーワード検証エラー

### フォールバック動作
- 特集キーワード機能エラー時 → 通常キーワード処理にフォールバック
- 新SDKエラー時 → 従来SDKにフォールバック
- スクレイピングエラー時 → エラーメッセージを返却

## ログ記録

### ログレベル
- `DEBUG`: 詳細なデバッグ情報
- `INFO`: 一般的な情報（処理開始、完了など）
- `WARNING`: 警告（フォールバック動作など）
- `ERROR`: エラー（処理失敗など）

### ログファイル
- `logs/app.log`: アプリケーションログ（ローテーション対応）
