# プロジェクト概要

## プロジェクト名
auto-title-generator（ヘアスタイルタイトルテンプレートジェネレーター）

## 目的
HotPepper Beautyからヘアスタイル情報をスクレイピングし、Google Gemini 2.5 Flash AIを使用して美容サロン向けのマーケティングテンプレート（タイトル、メニュー、コメント、ハッシュタグ）を自動生成するWebアプリケーション。

## 主な機能
- レディース/メンズのヘアスタイル選択
- HotPepper Beautyからのヘアスタイル情報の自動スクレイピング（非同期処理）
- AIによるタイトル、メニュー、コメント、ハッシュタグの自動生成
- 文字数のリアルタイム表示
- Beauty Selection特集キーワード連動機能（性別によるフィルタリング）
- テンプレートのカスタマイズとエクスポート

## 技術スタック

### バックエンド
- **Python**: 3.11.8（推奨バージョン）
- **Webフレームワーク**: Flask 3.0.2（ASGI対応、非同期ルート対応）
- **ASGIアダプター**: asgiref 3.8.1（WsgiToAsgi）

### AI・機械学習
- **AIモデル**: Google Gemini 2.5 Flash（デフォルトモデル、ユーザー選択不要）
- **SDK**: デュアルSDK構成
  - google-genai 1.27.0（新SDK、thinking_budget対応、優先使用）
  - google-generativeai 0.8.5（従来SDK、フォールバック用）
- **最適化**: thinking_budget=0設定で約70%の高速化を実現（20件テンプレート生成に約8-10秒）

### スクレイピング
- **HTTPクライアント**: aiohttp 3.9.3（完全非同期処理）
- **HTMLパーサー**: BeautifulSoup4 4.12.3
- **同期HTTP**: requests 2.31.0（補助的）

### フロントエンド
- HTML, CSS, JavaScript（バニラJS、フレームワーク不使用）
- ブルーテーマの統一デザイン

### 本番環境
- **WSGI/ASGIサーバー**: Gunicorn 21.2.0 + Uvicorn 0.29.0
- **デプロイプラットフォーム**: Render（Starterプラン対応）
- **ワーカー数**: 2（メモリ最適化）
- **メモリリーク対策**: max_requests=1000

### テスト
- **テストフレームワーク**: pytest 8.1.1（非同期テスト対応）
- **HTTPモック**: responses 0.24.1
- **UIテスト**: Selenium（オプション、環境変数で制御）

### 設定管理
- **環境変数管理**: python-dotenv 1.0.1

## アーキテクチャ

### コアコンポーネント
1. **app/__init__.py**: Flaskアプリケーションファクトリーパターン（create_app関数）
2. **app/main.py**: ブループリント、ルーティング、エラーハンドリング
3. **app/scraping.py**: HotPepperScraperクラス（非同期スクレイピング）
4. **app/generator.py**: TemplateGeneratorクラス（AI生成、デュアルSDK対応）
5. **app/config.py**: 設定管理（環境変数、季節キーワード、文字数制限）
6. **app/featured_keywords.py**: FeaturedKeywordsManagerクラス（特集キーワード管理）

### 非同期処理パイプライン
1. ユーザーがキーワード + 性別 + 季節（オプション）を送信
2. HotPepperScraper.scrape_titles_async()が非同期でヘアスタイルタイトルをスクレイピング
3. TemplateGenerator.generate_templates_async()がGemini 2.5 Flash APIに送信
4. 生成されたテンプレートを文字数制限で検証
5. JSONレスポンスをフロントエンドに返却

### デザインパターン
- **Async Context Managers**: セッション管理にasync withを使用
- **Error Boundary Pattern**: 包括的なエラーハンドリングとエラーコード
- **Template Validation**: 文字数制限とキーワード検証
- **Rate Limiting**: スクレイピングリクエスト間の設定可能な待機時間

## データフロー
1. フロントエンドからキーワード、性別、季節を送信
2. 特集キーワード判定（FeaturedKeywordsManager）
3. 非同期スクレイピング（HotPepper Beauty）
4. AI生成（Gemini 2.5 Flash、thinking_budget=0）
5. テンプレート検証（文字数制限）
6. JSONレスポンス返却

## パフォーマンス特性
- **AI生成速度**: 20件テンプレート生成に約8-10秒（従来比約70%高速化）
- **非同期処理**: 完全async/awaitパイプライン
- **リソース最適化**: MAX_PAGES=1（本番環境）、メモリリーク対策
- **デュアルSDK**: 新SDK優先、自動フォールバックで高い可用性
