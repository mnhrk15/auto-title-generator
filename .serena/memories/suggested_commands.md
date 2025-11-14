# 推奨コマンド

## 開発環境セットアップ

### 仮想環境の作成と有効化
```bash
# 仮想環境の作成
python -m venv .venv

# 仮想環境の有効化（macOS/Linux）
source .venv/bin/activate

# 仮想環境の有効化（Windows）
.venv\Scripts\activate
```

### 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### 環境変数の設定
```bash
# .env.exampleをコピーして.envを作成
cp .env.example .env

# .envファイルを編集して以下を設定：
# GEMINI_API_KEY=your_gemini_api_key_here（必須）
# FLASK_SECRET_KEY=your_secret_key_here
# FLASK_DEBUG=True
# SCRAPING_DELAY_MIN=1
# SCRAPING_DELAY_MAX=3
# MAX_PAGES=3
```

## アプリケーション実行

### 開発サーバー起動
```bash
python run.py
```
アプリケーションは http://localhost:5000 で起動します。

### 本番サーバー起動（Gunicorn）
```bash
gunicorn asgi:app -c gunicorn.conf.py
```

## テスト実行

### すべてのテストを実行
```bash
pytest tests/
```

### 非同期テスト対応モードで実行（推奨）
```bash
pytest tests/ --asyncio-mode=auto
```

### 特定のテストファイルを実行
```bash
# ジェネレーター機能のテスト
pytest tests/test_generator.py -v

# スクレイピング機能のテスト
pytest tests/test_scraping.py -v

# メインAPIのテスト
pytest tests/test_main.py -v

# 特集キーワード機能のテスト
pytest tests/test_featured_keywords.py -v
pytest tests/test_featured_integration.py -v
```

### UIテストを除外して実行（Seleniumが無い場合）
```bash
pytest tests/ -k "not test_ui"
```

### 統合テストを実行（実APIキー必要）
```bash
pytest tests/test_integration.py -v
```

### 特集キーワードUIテストを実行（環境変数必要）
```bash
RUN_UI_TESTS=1 pytest tests/test_featured_ui.py -v
```

### カバレッジレポート付きで実行
```bash
# 全体のカバレッジ
pytest tests/ --cov=app --cov-report=html

# 特集キーワード機能のカバレッジ
pytest tests/test_featured_*.py --cov=app.featured_keywords --cov-report=html
```

### 詳細出力で実行（デバッグ用）
```bash
pytest tests/ -vvs --tb=long
```

## デプロイ

### Renderへのデプロイ
1. GitHubリポジトリを準備
2. Renderダッシュボードで「New」→「Web Service」を選択
3. リポジトリを連携
4. 環境変数を設定（GEMINI_API_KEY必須）
5. デプロイ開始

**Start Command**: `gunicorn asgi:app -c gunicorn.conf.py`

## システムユーティリティコマンド（macOS/Darwin）

### ファイル操作
```bash
# ディレクトリ一覧
ls -la

# ディレクトリ移動
cd /path/to/directory

# ファイル検索
find . -name "*.py"

# パターン検索
grep -r "pattern" .
```

### Git操作
```bash
# ステータス確認
git status

# 変更をステージング
git add .

# コミット
git commit -m "commit message"

# プッシュ
git push origin branch-name
```

## ログ確認

### アプリケーションログ
```bash
# ログファイルの確認
tail -f logs/app.log

# エラーログのみ確認
grep ERROR logs/app.log
```
