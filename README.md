# ヘアスタイルタイトルテンプレートジェネレーター

## 概要
このプロジェクトは、ヘアスタイルのタイトル、メニュー、コメント、ハッシュタグを自動生成するWebアプリケーションです。美容師やヘアサロンのスタッフが、SNSでの投稿や記事作成を効率的に行うことができます。

## 主な機能
- レディース/メンズのヘアスタイル選択
- ヘアスタイル情報の自動スクレイピング
- タイトル、メニュー、コメント、ハッシュタグの自動生成
- **季節・カラーの複合選択**（レディースのみ・任意）
- **メンズ向けのスタイル名補完ガイド**（結果画面の注釈）
- 文字数のリアルタイム表示
- テンプレートのカスタマイズとエクスポート
- **🌟 Beauty Selection特集キーワード連動機能**（NEW）
  - トレンド特集キーワードのワンクリック選択
  - 特集掲載条件を満たした高品質テンプレート生成

## 技術スタック
- **バックエンド**: Python 3.11.8, Flask 3.0.2 (ASGI対応)
- **AI**: Google Gemini 3 Flash Preview (thinkingLevel=MINIMALで高速化、デフォルトモデル)
- **SDK**: google-genai 1.70.0
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

## 季節・カラー選択とメンズ向け注釈

### 季節・カラー選択（レディースのみ）
検索フォームの下に「春 / 夏 / 秋 / 冬 / ブリーチなしカラー」のチェックボックスがあり、複数選択できます（全て未チェックでも構いません）。

- **プロンプトには季節語を一切注入しません。** チェックされた語は、AI生成が完了したあとの Python 後処理でタイトル末尾に `◎春カラー` の形で付加されます
- 付加されるのは **26文字未満** のタイトルのみで、付加後に上限30文字を超える場合は付加しません
- 複数チェック時は対象タイトルへ均等に配分されます。長いキーワード（`ブリーチなしカラー`）ほど収まるタイトルが限られるため、余白の大きい短いタイトルから優先的に割り当てます
- 区切り記号にはバリエーションを持たせています。タイトルがすでに `/` や `×` を使っていればその記号に合わせ（複数あれば末尾に近いもの）、記号のないタイトルには `◎` → `/` → `×` の順にローテーションで割り当てます

  ```
  美髪パーマ/艶髪/レイヤーカット/ブリーチなしカラー   ← タイトルの「/」に合わせる
  小顔レイヤーボブ×ニュアンスパーマ×冬カラー         ← タイトルの「×」に合わせる
  髪質改善パーマボブ◎冬カラー                        ← 記号なしなのでローテーション
  ```

- 付加の余白を確保するため、チェックがある場合のみ短めのタイトル枠をプロンプトで指示します。**付加後にちょうど30文字へ届くよう、語の長さごとに目標帯を分けます**

  | 付加する語 | 区切り込みの長さ | 目標帯 | 付加後 |
  |---|---|---|---|
  | 春/夏/秋/冬カラー | 5文字 | 23〜25文字 | 28〜30文字 |
  | ブリーチなしカラー | 10文字 | 18〜20文字 | 28〜30文字 |

  1つあたりの枠数は `min(4, 12 ÷ チェック数)` で、合計12枠を超えないよう調整されます。
  例: 「冬」＋「ブリーチなしカラー」→ `20個中4個は23〜25文字、4個は18〜20文字、残りの12個は25〜28文字`

- 後処理はタイトル側ではなく**キーワード側から**割り当てます。付加済み件数が最も少ない語から順に、**その語が収まる範囲で最も長いタイトル**を選ぶため、均等配分を保ちながら各タイトルが30文字に近づきます。結果として、余白の大きい短いタイトルには `ブリーチなしカラー` が、余白の小さいタイトルには `春カラー` が自然に振り分けられます

関連する設定は `app/config.py` の `SEASON_COLOR_CHOICES` / `SEASON_APPEND_SEPARATORS` / `SEASON_APPEND_DELIMITERS` / `SEASON_APPEND_THRESHOLD` / `SHORT_TITLE_*` にまとまっています。

### メンズ
- 季節カラー（春/夏/秋/冬カラー）とブリーチなしカラーは、プロンプト・後処理のいずれでも**一切適用されません**。季節・カラーのチェックボックス自体が非表示になり、サーバ側でも `seasons` は無視されます
- プロンプト内の語彙例・タイトル例・メニュー例・コメント例・ハッシュタグ例は、すべてメンズ向けのものに切り替わります
- 結果画面の見出し直下に「スタイル名が30文字のキーワードになるよう…」という注釈バナーを表示し、「足す語の例」を折りたたみで提示します（この語彙リストは表示専用で、プロンプトには注入しません）

## 🌟 Beauty Selection特集キーワード機能

### 概要
HotPepper Beautyの「Beauty Selection」特集に掲載される可能性の高いテンプレートを生成する機能です。特集キーワードを使用することで、Beauty Selectionの掲載条件を満たした高品質なマーケティングテンプレートを自動生成できます。性別によるリアルタイムフィルタリング機能を搭載し、レディース・メンズ選択時に対応する特集キーワードのみが表示されます。

### 主な特徴
- **ワンクリック選択**: 現在のトレンド特集キーワードをボタン一つで選択
- **性別別フィルタリング**: レディース・メンズ選択時に対応するキーワードのみ表示
- **リアルタイム更新**: 性別変更時に自動的にキーワードリストを更新
- **特集対応プロンプト**: Beauty Selection掲載条件を組み込んだ強化プロンプト
- **シンプルUI**: 不要な通知やポップアップを排除した直感的なデザイン
- **フォールバック機能**: 特集機能エラー時も通常機能で継続動作

### 使用方法

#### 1. 特集キーワードの確認
- アプリケーション起動時に「特集キーワード」セクションが表示されます
- 現在特集されているトレンドキーワードがボタン形式で表示されます
- 性別選択に応じて対応するキーワードのみが表示されます（リアルタイム更新）

#### 2. 性別による動的フィルタリング
- **レディース選択時**: レディース向け特集キーワードのみ表示
- **メンズ選択時**: メンズ向け特集キーワードのみ表示
- 性別変更時に自動的にキーワードリストが更新されます

#### 3. キーワード選択とUI
- 特集キーワードボタンをクリックするだけで以下が自動実行されます：
  - キーワード入力欄への自動入力
  - 選択中キーワードの視覚的フィードバック（ブルーテーマ）
  - スムーズなキーワード変更（確認ダイアログやポップアップ無し）
- **シンプルデザイン**: 不要な通知やマークを排除したクリーンなUI

#### 4. 特集対応テンプレート生成
- 「テンプレート生成」ボタンをクリック
- 特集掲載条件を満たしたテンプレートが生成されます
- 生成されたテンプレートには特集対応マークが表示されます

### UI・デザイン仕様

#### カラーテーマ
- **メインカラー**: ブルー系統（#4da6ff, #66b3ff）を採用
- **アクセントカラー**: 特集キーワード選択時のハイライト表示
- **統一感**: 全体のUI要素でブルーテーマを統一使用

#### UX改善点
- **通知の削除**: 特集キーワード選択時のポップアップ通知を無効化
- **確認ダイアログの削除**: キーワード変更時の警告ダイアログを削除
- **クリーンデザイン**: 不要な視覚要素（星マーク等）を排除
- **直感的操作**: ワンクリックでスムーズなキーワード選択

### 特集キーワードの管理

#### データファイル形式
特集キーワードは `app/data/featured_keywords.json` で管理されます。

```json
[
  {
    "name": "くびれヘア",
    "keyword": "くびれヘア", 
    "gender": "ladies",
    "condition": "スタイル名に『くびれヘア』という文言を必ず含めること。顔周りと首元の曲線美を強調し、小顔効果のあるエレガントなスタイルを表現してください。"
  },
  {
    "name": "サーフカール",
    "keyword": "サーフカール",
    "gender": "mens",
    "condition": "スタイル名に『サーフカール』という文言を含めること。海上がりのような無造作感と爽やかさを演出し、夏に似合うリラックスしたスタイルを表現してください。"
  }
]
```

#### 更新手順
1. `app/data/featured_keywords.json` ファイルを編集
2. アプリケーションを再起動（本番環境では再デプロイ）
3. 新しい特集キーワードが自動的に反映されます

### トラブルシューティング

#### 特集キーワードが表示されない場合
1. **JSONファイルの確認**: `app/data/featured_keywords.json` が存在し、正しい形式であることを確認
2. **ファイル権限**: JSONファイルの読み込み権限を確認
3. **ログ確認**: アプリケーションログでエラーメッセージを確認
4. **フォールバック動作**: 特集機能エラー時も通常のテンプレート生成は継続動作します

#### 特集キーワード選択が動作しない場合
1. **JavaScript有効化**: ブラウザでJavaScriptが有効になっていることを確認
2. **ネットワーク接続**: APIエンドポイント `/api/featured-keywords` への接続を確認
3. **ブラウザ互換性**: モダンブラウザ（Chrome, Firefox, Safari, Edge最新版）の使用を推奨

#### 特集テンプレート生成で問題が発生した場合
1. **API接続確認**: Gemini APIキーが正しく設定されていることを確認
2. **ログ確認**: 特集対応プロンプト生成のエラーログを確認
3. **フォールバック**: 特集機能エラー時は通常プロンプトでテンプレート生成を継続

### API仕様

#### 特集キーワード取得API
```
GET /api/featured-keywords?gender={ladies|mens}
```

**リクエストパラメータ:**
- `gender` (オプション): `ladies` または `mens` - 指定された性別のキーワードのみ取得

**レスポンス例:**
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

#### テンプレート生成API
```
POST /api/generate
```

**リクエストパラメータ:**

| パラメータ | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `keyword` | string | ✓ | - | 検索キーワード（スペース・読点・`/` などで複数指定可） |
| `gender` | string | - | `ladies` | `ladies` または `mens`。それ以外は 400 |
| `seasons` | string[] | - | `[]` | 季節・カラーの複合選択。`spring` / `summer` / `autumn` / `winter` / `bleach_free`。未知の値は無視され、`gender=mens` では常に空として扱われる。配列以外を渡すと 400 |
| `model` | string | - | `gemini-3.1-flash-lite` | 生成モデル。未対応の値はデフォルトにフォールバック |

**リクエスト例:**
```json
{
  "keyword": "髪質改善",
  "gender": "ladies",
  "seasons": ["spring", "bleach_free"],
  "model": "gemini-3.1-flash-lite"
}
```

特集キーワードは `keyword` から自動判定され、特集対応テンプレートが生成されます。

**特集テンプレートレスポンス例:**
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

## プロジェクト構造
```
template-generator/
├── app/
│   ├── main.py              # メインアプリケーションロジック
│   ├── scraping.py          # スクレイピング機能
│   ├── generator.py         # テンプレート生成ロジック
│   ├── featured_keywords.py # 特集キーワード管理クラス
│   ├── config.py            # 設定ファイル
│   ├── data/
│   │   └── featured_keywords.json  # 特集キーワードデータファイル
│   ├── static/              # 静的ファイル（CSS, JS等）
│   └── templates/           # HTMLテンプレート
├── tests/                   # テストファイル
│   ├── test_featured_keywords.py     # 特集キーワード機能テスト
│   ├── test_featured_integration.py  # 特集機能統合テスト
│   └── test_featured_ui.py          # 特集機能UIテスト
├── requirements.txt         # 依存パッケージリスト
└── run.py                  # アプリケーション起動スクリプト
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
- **AI エンジン**: Google Gemini 3 Flash Preview使用（デフォルトモデル、ユーザー選択不要）
- **高速化**: thinkingLevel=MINIMAL設定で思考プロセスを最小化
- **SDK**: google-genai 1.70.0
- **非同期処理**: 完全async/await対応で高いスループット
- **性別別プロンプト**: レディース／メンズで語彙例・タイトル例・メニュー例・コメント例を切り替え
- **季節・カラー後処理**: `_apply_season_keywords()` が生成後のタイトルへ選択キーワードを均等配分で付加

### config.py
- アプリケーション設定の管理
- 環境変数の読み込みと設定
- ホスト設定やその他のパラメータ管理
- 季節・カラー選択肢（`SEASON_COLOR_CHOICES`）と付加ルールの定数

### featured_keywords.py
- **特集キーワード管理**: JSONファイルからの特集キーワード読み込み
- **性別フィルタリング**: 性別に基づく動的キーワードフィルタリング機能
- **キーワード判定機能**: 入力キーワードが特集キーワードかを自動判定
- **エラーハンドリング**: ファイル読み込みエラー時のフォールバック処理
- **ヘルスチェック**: 特集キーワード機能の状態監視と診断
- **リアルタイム更新**: 性別変更時の即座なキーワードリスト更新

## テスト

### テスト構成
- **test_generator.py**: AI生成機能（非同期対応）
- **test_scraping.py**: スクレイピング機能（aiohttp mock使用）
- **test_main.py**: Flask API エンドポイント（非同期ルート対応）
- **test_integration.py**: エンドツーエンドテスト（実APIキー必要）
- **test_ui.py**: フロントエンド機能（Selenium、自動スキップ対応）
- **test_featured_keywords.py**: 特集キーワード管理機能のユニットテスト
- **test_featured_integration.py**: 特集キーワード機能のAPI統合テスト
- **test_featured_ui.py**: 特集キーワード機能のUIテスト（Selenium対応）

### テスト実行方法
```bash
# すべてのテストを実行
pytest tests/

# 非同期テスト対応モードで実行
pytest tests/ --asyncio-mode=auto

# UIテストを除外して実行（Seleniumが無い場合）
pytest tests/ -k "not test_ui"

# 特集キーワード機能のテストのみ実行
pytest tests/test_featured_keywords.py tests/test_featured_integration.py -v

# 特集キーワードUIテストを実行（RUN_UI_TESTS=1が必要）
RUN_UI_TESTS=1 pytest tests/test_featured_ui.py -v

# 特定のテストファイルのみ実行
pytest tests/test_generator.py -v

# カバレッジ付きで実行
pytest tests/ --cov=app

# 特集キーワード機能のカバレッジレポート
pytest tests/test_featured_*.py --cov=app.featured_keywords --cov-report=html
```

## パフォーマンス特性

### AI生成速度
- **Gemini 3 Flash Preview**: デフォルトモデル使用（ユーザー選択不要）
- **thinkingLevel=MINIMAL**: 思考プロセス最小化で高速化
- **SDK**: google-genai 1.70.0

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
   - **Gemini 3 Flash Preview**: デフォルトAIモデル使用（ユーザー選択不要）
   - **thinkingLevel=MINIMAL**: 思考プロセス最小化で高速化
   - **非同期処理**: 完全async/awaitパイプライン
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