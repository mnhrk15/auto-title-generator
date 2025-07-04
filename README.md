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
- バックエンド: Python (Flask)
- フロントエンド: HTML, CSS, JavaScript
- スクレイピング: BeautifulSoup4, aiohttp

## セットアップ方法

### 前提条件
- Python 3.8以上
- pip (Pythonパッケージマネージャー)

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
# .envファイルを編集して必要な設定を行う
```

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
- ヘアスタイル情報のスクレイピング機能
- レディース/メンズそれぞれのURLに対応
- エラーハンドリングを実装

### generator.py
- テンプレートの生成ロジック
- タイトル、メニュー、コメント、ハッシュタグの自動生成
- 柔軟なプロンプトエンジニアリング

### config.py
- アプリケーション設定の管理
- 環境変数の読み込みと設定
- ホスト設定やその他のパラメータ管理

## テスト
テストの実行方法：
```bash
pytest tests/
```

## 注意事項
- スクレイピングの際は対象サイトのロボット規約を遵守してください
- 生成されたテンプレートは必ず内容を確認してから使用してください
- 文字数制限に注意してください（プラットフォームごとに異なる場合があります）

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
     - **Start Command**: `gunicorn run:app`

3. 環境変数の設定
   - 「Environment」タブを開き、以下の環境変数を設定します：
     - **GEMINI_API_KEY**: Gemini APIキー（必須）
     - **FLASK_SECRET_KEY**: セキュアなランダム文字列（renderが自動生成）
     - **FLASK_DEBUG**: `False`（本番環境では推奨）
     - その他必要な環境変数（render.yamlで設定済み）

4. デプロイを開始
   - 「Create Web Service」をクリックしてデプロイを開始します
   - デプロイが完了すると、Renderが提供するURLでアプリにアクセスできます（例：https://template-generator.onrender.com）

5. カスタムドメインの設定（オプション）
   - 「Settings」タブの「Custom Domain」セクションからカスタムドメインを設定できます

#### 注意点
- 無料プランでは、一定時間使用がないとサービスがスリープ状態になります
- 初回のデプロイには数分かかることがあります
- APIキーなどの機密情報は必ず環境変数を通じて設定し、Gitリポジトリにはコミットしないでください 