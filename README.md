# ヘアスタイルタイトルテンプレートジェネレーター

## 概要
このプロジェクトは、ヘアスタイルのタイトル、メニュー、コメント、ハッシュタグを自動生成するWebアプリケーションです。美容師やヘアサロンのスタッフが、SNSでの投稿や記事作成を効率的に行うことができます。

## 主な機能
- レディース/メンズのヘアスタイル選択
- ヘアスタイル情報の自動スクレイピング
- タイトル、メニュー、コメント、ハッシュタグの自動生成
- 文字数のリアルタイム表示
- テンプレートのカスタマイズとエクスポート

## 技術スタック
- **バックエンド**: Python 3.11.8, Flask 3.0.2 (ASGI対応)
- **AI**: Google Gemini 2.5 Flash Lite (thinking_budget=0で超高速化)
- **SDK**: デュアルSDK構成
  - google-genai 1.27.0 (新SDK、thinking_budget対応)
  - google-generativeai 0.8.5 (従来SDK、フォールバック用)
- **フロントエンド**: HTML, CSS, JavaScript
- **スクレイピング**: BeautifulSoup4 4.12.3, aiohttp 3.9.3 (完全非同期処理)
- **本番環境**: Gunicorn 21.2.0 + Uvicorn 0.29.0 (ASGI対応)
- **テスト**: pytest 8.1.1 (非同期テスト対応)

## セットアップ方法

### 前提条件
- **Python 3.11.8以上** (推奨バージョン)
- pip (Pythonパッケージマネージャー)
- **Google Gemini API キー** ([Google AI Studio](https://makersuite.google.com/app/apikey)で取得)

### インストール手順
1. リポジトリのクローン
```bash
git clone https://github.com/mnhrk/template-generator.git
cd template-generator
```

2. 仮想環境の作成と有効化
```bash
python -m venv .venv
source .venv/bin/activate  # Unix系
# または
.venv\Scripts\activate  # Windows
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集して以下の必須設定を行う：

# 必須設定
GEMINI_API_KEY=your_gemini_api_key_here

# オプション設定（開発環境用）
FLASK_SECRET_KEY=your_secret_key_here
FLASK_DEBUG=True
SCRAPING_DELAY_MIN=1
SCRAPING_DELAY_MAX=3
MAX_PAGES=3
```

**重要**: Google Gemini APIキーが必須です。[Google AI Studio](https://makersuite.google.com/app/apikey)で取得してください。

### 実行方法
```bash
python run.py
```
アプリケーションは http://localhost:5000 で起動します。

## プロジェクト構造
```
template-generator/
├── app/
│   ├── main.py          # メインアプリケーションロジック
│   ├── scraping.py      # スクレイピング機能
│   ├── generator.py     # テンプレート生成ロジック
│   ├── config.py        # 設定ファイル
│   ├── static/          # 静的ファイル（CSS, JS等）
│   └── templates/       # HTMLテンプレート
├── tests/               # テストファイル
├── requirements.txt     # 依存パッケージリスト
└── run.py              # アプリケーション起動スクリプト
```

## 主要コンポーネントの説明

### main.py
- Flaskアプリケーションのメインエントリーポイント
- ルーティングとリクエストハンドリングを担当
- フロントエンドとバックエンドの連携を管理

### scraping.py
- **非同期スクレイピング**: aiohttp 3.9.3使用で高速並行処理
- **対象サイト**: HotPepper Beauty (レディース/メンズ両対応)
- **レート制限**: 設定可能な待機時間でサイト負荷を軽減
- **SSL対応**: 開発/本番環境で自動切り替え
- **エラーハンドリング**: 包括的な例外処理とログ出力
- **セッション管理**: async context managerで適切なリソース管理

### generator.py
- **AI エンジン**: Google Gemini 2.5 Flash Lite使用（最高速モデル）
- **超高速化**: thinking_budget=0設定で最大71%の高速化を実現
- **デュアルSDK**: 新SDK優先、自動フォールバック機能付き
  - 新SDK: google-genai 1.27.0 (thinking_budget対応)
  - 従来SDK: google-generativeai 0.8.5 (互換性維持)
- **性能**: 20件のテンプレートを約8秒で生成
- **非同期処理**: 完全async/await対応で高いスループット

### config.py
- アプリケーション設定の管理
- 環境変数の読み込みと設定
- ホスト設定やその他のパラメータ管理

## テスト

### テスト構成
- **test_generator.py**: AI生成機能（非同期対応）
- **test_scraping.py**: スクレイピング機能（aiohttp mock使用）
- **test_main.py**: Flask API エンドポイント（非同期ルート対応）
- **test_integration.py**: エンドツーエンドテスト（実APIキー必要）
- **test_ui.py**: フロントエンド機能（Selenium、自動スキップ対応）

### テスト実行方法
```bash
# すべてのテストを実行
pytest tests/

# 非同期テスト対応モードで実行
pytest tests/ --asyncio-mode=auto

# UIテストを除外して実行（Seleniumが無い場合）
pytest tests/ -k "not test_ui"

# 特定のテストファイルのみ実行
pytest tests/test_generator.py -v

# カバレッジ付きで実行
pytest tests/ --cov=app
```

## パフォーマンス特性

### AI生成速度
- **Gemini 2.5 Flash Lite**: 最高速度モデル使用
- **thinking_budget=0**: 思考プロセス無効化で超高速化
- **実測値**: 20件テンプレート生成に約8秒
- **改善率**: 従来比71%高速化

### デュアルSDK アーキテクチャ
- **新SDK (Primary)**: google-genai 1.27.0
  - thinking_budget=0 対応で超高速化
  - 最新のGemini 2.5 Flash Lite最適化
- **従来SDK (Fallback)**: google-generativeai 0.8.5
  - 後方互換性の維持
  - 新SDK失敗時の自動フォールバック
- **パフォーマンス**: 新SDK使用時は71%高速化を実現
- **信頼性**: デュアル構成により高い可用性を確保

### 非同期処理アーキテクチャ
- **Flask 3.0.2**: ASGI対応で非同期ルート処理
- **aiohttp 3.9.3**: 高速非同期HTTPクライアント
- **async/await**: 全パイプライン非同期化
  - スクレイピング: `scrape_titles_async()`
  - AI生成: `generate_templates_async()`
  - API処理: `/api/generate` 非同期エンドポイント
- **セッション管理**: async context managerによる適切なリソース管理
- **ASGI適用**: asgi.py による Flask ⇔ ASGI ブリッジ

## 注意事項
- スクレイピングの際は対象サイトのロボット規約を遵守してください
- 生成されたテンプレートは必ず内容を確認してから使用してください
- 文字数制限に注意してください（プラットフォームごとに異なる場合があります）
- **重要**: Gemini APIキーは機密情報です。環境変数で管理し、リポジトリにコミットしないでください

## ライセンス
このプロジェクトはMITライセンスの下で公開されています。

## 貢献
バグ報告や機能改善の提案は、GitHubのIssueを通じてお願いします。
プルリクエストも歓迎します。

## クラウドデプロイ手順

### Renderへのデプロイ

本アプリケーションはRenderを使用して簡単にデプロイできます。

#### 前提条件
- GitHubアカウント
- Renderアカウント ([Render公式サイト](https://render.com)で無料登録可能)
- Google GeminiのAPIキー

#### デプロイ手順

1. GitHubリポジトリの準備
   - このリポジトリをフォークするか、自分のGitHubアカウントに新しくリポジトリを作成してコードをプッシュします

2. Renderダッシュボードでのデプロイ
   - Renderにログインして「New」→「Web Service」を選択
   - GitHubリポジトリと連携し、デプロイしたいリポジトリを選択
   - 以下の設定を入力します：
     - **Name**: template-generator（任意の名前）
     - **Environment**: Python
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn asgi:app -c gunicorn.conf.py`

3. 環境変数の設定
   - 「Environment」タブを開き、以下の環境変数を設定します：
     - **GEMINI_API_KEY**: Gemini APIキー（必須）
     - **FLASK_SECRET_KEY**: セキュアなランダム文字列（renderが自動生成）
     - **FLASK_DEBUG**: `False`（本番環境では推奨）
     - その他必要な環境変数（render.yamlで設定済み）

   **パフォーマンス最適化**: 
   - **Gemini 2.5 Flash Lite**: 最高速度AIモデル使用
   - **thinking_budget=0**: 思考プロセス無効化で超高速化
   - **デュアルSDK**: 新SDK優先、自動フォールバック
   - **非同期処理**: 完全async/awaitパイプライン
   - **実測値**: 20件テンプレート生成を約8秒で完了（71%高速化）
   - **リソース最適化**: MAX_PAGES=1でスクレイピング高速化

4. デプロイを開始
   - 「Create Web Service」をクリックしてデプロイを開始します
   - デプロイが完了すると、Renderが提供するURLでアプリにアクセスできます（例：https://template-generator.onrender.com）

5. カスタムドメインの設定（オプション）
   - 「Settings」タブの「Custom Domain」セクションからカスタムドメインを設定できます

#### 注意点
- 無料プランでは、一定時間使用がないとサービスがスリープ状態になります
- 初回のデプロイには数分かかることがあります
- APIキーなどの機密情報は必ず環境変数を通じて設定し、Gitリポジトリにはコミットしないでください 