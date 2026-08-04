from google import genai
from google.genai import types
from typing import List, Dict, Tuple, Optional
import json
import logging
import asyncio
import re
from . import config

# ロガーの設定
logger = logging.getLogger(__name__)

class TemplateGenerator:
    def __init__(self, model_name='gemini-3.1-flash-lite'):
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")

        # サポートされているモデルの検証
        supported_models = ['gemini-3.1-flash-lite', 'gemini-3-flash-preview']
        if model_name not in supported_models:
            logger.warning(f"Unsupported model: {model_name}, falling back to gemini-3.1-flash-lite")
            model_name = 'gemini-3.1-flash-lite'

        self.model_name = model_name

        # Google GenAI SDKクライアント初期化
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        logger.info(f"TemplateGeneratorが初期化されました（モデル: {model_name}）")
        
    @staticmethod
    def _short_title_slots_per_keyword(selected_count: int) -> int:
        """季節・カラー1つあたりに割り当てる短尺タイトル枠の数"""
        return max(1, min(
            config.SHORT_TITLE_SLOTS_PER_CHOICE,
            config.SHORT_TITLE_SLOTS_MAX // selected_count
        ))

    @staticmethod
    def _short_title_band_max(keyword: str) -> int:
        """このキーワードを付加してちょうど上限文字数に収まる、付加前のタイトル文字数"""
        # 区切り記号1文字ぶんを差し引く。付加対象にならない長さを指示しないよう閾値未満に抑える
        return min(
            config.CHAR_LIMITS['title'] - 1 - len(keyword),
            config.SEASON_APPEND_THRESHOLD - 1
        )

    def _normalize_seasons(self, seasons: Optional[List[str]], gender: str) -> List[str]:
        """季節・カラー選択値を config の定義順に正規化する（未知値と重複を除去）

        メンズでは季節カラー／ブリーチなしカラーを一切扱わないため常に空リストを返す。
        """
        if gender == 'mens' or not seasons:
            return []
        return [key for key in config.SEASON_COLOR_CHOICES if key in seasons]

    def _create_prompt(self, titles: List[str], keyword: str, seasons: List[str] = None, gender: str = 'ladies', featured_info: Dict = None, generation_context: Dict = None) -> str:
        """プロンプトテンプレートの作成"""
        titles_json = json.dumps(titles, ensure_ascii=False, indent=2)

        # 性別に応じた設定
        gender_name = "レディース" if gender == 'ladies' else "メンズ"
        is_mens = gender == 'mens'

        selected_seasons = self._normalize_seasons(seasons, gender)

        # 混在キーワード処理のための生成コンテキスト解析
        context = generation_context or {}
        keyword_type = context.get('keyword_type', 'normal')
        processing_mode = context.get('processing_mode', 'standard')
        original_keyword = context.get('original_keyword', keyword)
        
        # 特集キーワード用のプロンプト強化ロジック（混在処理対応）
        featured_instruction = ""
        if featured_info:
            try:
                # 特集情報の検証
                if not isinstance(featured_info, dict):
                    logger.warning(f"特集情報が辞書形式ではありません: {type(featured_info)} - 特集機能をスキップ")
                elif 'condition' not in featured_info or not featured_info['condition']:
                    logger.warning("特集情報に条件が含まれていません - 特集機能をスキップ")
                else:
                    condition = str(featured_info['condition']).strip()
                    if len(condition) > 1000:  # 条件文の長さ制限
                        logger.warning(f"特集条件文が長すぎます ({len(condition)} > 1000文字) - 切り詰めます")
                        condition = condition[:1000] + "..."
                    
                    # 混在キーワード処理に応じた指示文の調整
                    if keyword_type == "mixed":
                        featured_instruction = f"""

【重要】特集掲載条件の厳守（混在キーワード処理）
入力されたキーワード「{original_keyword}」には特集キーワード「{featured_info.get('name', keyword)}」が含まれています。
以下の特集掲載条件を絶対に満たすテンプレートを生成してください：

{condition}

混在キーワード処理のため、特集キーワードの条件を最優先としつつ、
他のキーワード要素も適切に組み込んでください。
特集掲載の対象外とならないよう、上記の条件を厳密に守ってください。

"""
                    else:
                        featured_instruction = f"""

【重要】特集掲載条件の厳守
このキーワード「{keyword}」は今月の特集キーワードです。
以下の条件を絶対に満たすテンプレートを生成してください：

{condition}

この条件を満たさないテンプレートは特集掲載の対象外となるため、
必ず上記の条件を最優先事項として考慮してください。
特に、タイトル生成時には上記の条件を厳密に守り、
指定されたキーワードや表現を必ず含めるようにしてください。

"""
                    logger.debug(f"特集プロンプト強化を適用: キーワード '{keyword}', タイプ: {keyword_type}")
            except Exception as e:
                logger.error(f"特集プロンプト生成中にエラー: {str(e)} - 特集機能をスキップ")
                featured_instruction = ""

        # タイトルの目標文字数（季節・カラー選択時は、後処理で語句を付加する余白を確保するため
        # 一部を短めに生成させる。付加語の長さごとに目標帯を分け、付加後に上限文字数へ届くようにする）
        title_length_rule = "- title: **25〜28文字**を目標"
        short_title_note = ""
        if selected_seasons:
            slots_per_keyword = self._short_title_slots_per_keyword(len(selected_seasons))
            bands = {}
            for key in selected_seasons:
                band_max = self._short_title_band_max(config.SEASON_COLOR_CHOICES[key])
                bands[band_max] = bands.get(band_max, 0) + slots_per_keyword
            short_slots = sum(bands.values())
            band_rules = "、".join(
                f"**{slots}個は{band_max - config.SHORT_TITLE_BAND_WIDTH}〜{band_max}文字**"
                for band_max, slots in sorted(bands.items(), reverse=True)
            )
            title_length_rule = (
                f"- title: {config.MAX_TEMPLATES}個中{band_rules}、"
                f"残りの{config.MAX_TEMPLATES - short_slots}個は**25〜28文字**を目標"
            )
            short_title_note = (
                "\n※ 短めの目標文字数を指定しているのは、後から語句を追記するための余白を残す目的です。"
                "追記する語句はこちらで決めるため、指定は不要です。"
                "追記後に上限文字数いっぱいまで活用できるよう、指定した文字数の**上限側に寄せて**作成してください。\n"
            )
            logger.debug(f"短尺タイトル枠 {bands} をプロンプトに追加（選択: {selected_seasons}）")

        # メンズ固有の注意点（メンズの場合のみ）
        mens_note = ""
        if is_mens:
            mens_note = """
- **メンズ特有キーワードの活用:**
    - ターゲット層: メンズ、20代30代、社会人、学生
    - スタイル: ツーブロック、センターパート、フェード、マッシュ、ショート
    - 技術: パーマ、ツイスパ、ニュアンスパーマ、波巻きパーマ
    - 効果: 小顔効果、骨格補正、清潔感、爽やか
    - 用途: ビジネス、カジュアル、オフィス
    - トレンド: 韓国風、外国人風、モダン
"""

        # 性別に応じた語彙・例示（メンズにレディース向けカラー語が混入しないよう分岐する）
        if is_mens:
            keyword_examples = "（例: 20代30代 / 束感 / 韓国風 / 好印象）"
            title_keyword_hints = (
                "`小顔`, `束感`, `好印象`, `清潔感`, `爽やか`, `骨格補正`, `似合わせ`, `イメチェン`, "
                "`韓国風`, `外国人風`, `ツーブロック`, `センターパート`, `マッシュ`, `ウルフ`, `フェード`, "
                "`ニュアンスパーマ`, `ツイストパーマ`, `スパイラルパーマ` など"
            )
            specificity_hint = (
                "髪型（ショート, マッシュ, ウルフ, センターパート, ツーブロック, フェード）、"
                "技術（カット, パーマ, ツイストパーマ, スパイラルパーマ, 刈り上げ）、"
                "印象（小顔効果, 骨格補正, 清潔感, 束感）を複数組み合わせてください。"
            )
            title_examples = """- `小顔効果◎メンズパーマ波巻き×センターパート` (22文字) - ◎と×の組み合わせ
- `韓国風マッシュ/ニュアンスパーマ爽やか` (19文字) - /で区切り
- `韓国風マッシュニュアンスパーマ爽やか` (18文字) - 記号なし"""
            comment_examples = """- `頭の形が綺麗に見えるよう常に意識をしています！パーマをかけることでより骨格補正効果、スタイリングも簡単！学生はもちろん、社会人の方にもオススメ！黒髪相性良し！誰もが悩む絶壁、ハチ張り一緒に解消しましょう！` (102文字)
- `ツイストスパイラルパーマで今一番かっこいい髪型です♪ツイスパならではの動きを質感でだしつつ、やり過ぎない動きに仕上げました。ナチュラルでも、ウェットでも、ドライでも質感の好みやその日の気分で雰囲気を変えてもかっこよくキマります☆` (114文字)
- `マッシュショートの爽やかスタイル！時間のない朝にも時短でできる朝ラクヘア！10代から20代、30代から40代、50代と幅広く人気の王道スタイルです！外国人風の奥行きと骨格補正で似合わせバツグン！` (97文字)"""
            menu_examples = """- `カット+ツイストスパイラルパーマ+眉カット+スタイリング剤付き◎朝ラク時短で決まる束感ヘア` (45文字)
- `カット+ニュアンスパーマ+ヘッドスパ+眉カット込み◎骨格補正で小顔見えする韓国風マッシュ` (43文字)
- `カット+フェード+シェービング+スタイリング講習付き◎清潔感重視のビジネススタイル` (41文字)"""
            symbol_examples = """- 「◎」: キーワードの強調（例: 小顔効果◎センターパート）
- 「/」: キーワードの並列・区切り（例: マッシュ/韓国風/ニュアンスパーマ）
- 「◆」: 装飾・強調（例: 好印象メンズショート◆束感）
- 「×」: スタイルや技術の並列（例: ツーブロック×スパイラルパーマ）
- 記号なし: 自然な連結（例: 韓国風マッシュニュアンスパーマ爽やか）"""
            hashtag_examples = '- `["韓国風", "マッシュ", "ニュアンスパーマ", "無造作", "メンズヘア", "おしゃれ", "トレンド", "ヘアスタイル", "美容院", "カット"]`'
        else:
            keyword_examples = "（例: 20代30代 / 透明感 / 韓国風 / 小顔）"
            title_keyword_hints = (
                "`大人可愛い`, `小顔`, `美髪`, `艶髪`, `透明感`, `似合わせ`, `イメチェン`, `レイヤー`, `ウルフ`, "
                "`くびれ`, `韓国風`, `シースルーバング`, `髪質改善`, `暗髪`, `インナーカラー`, `ハイライト`, "
                "`バレイヤージュ`, `縮毛矯正`, `デジタルパーマ` など"
            )
            specificity_hint = (
                "髪型（ボブ, ミディアム, ロング, ショート, ウルフ, レイヤー）、"
                "色（アッシュ, ベージュ, グレージュ, ピンク, ラベンダー）、"
                "技術（カット, カラー, パーマ, トリートメント, ハイライト, ブリーチ）を複数組み合わせてください。"
            )
            title_examples = """- `大人可愛い透明感グレージュ◎20代美人ヘア` (21文字) - ◎で強調
- `韓国風レイヤーカット/顔周り/くびれミディ` (20文字) - /で3要素並列
- `上品韓国ヘア◆グレージュ顔周りカット` (18文字) - ◆で装飾
- `くびれミディ×艶髪ラベンダーカラー30代` (20文字) - ×で並列
- `ミディアムレイヤー顔周りカラー韓国ヘア` (19文字) - 記号なしの自然連結
- `韓国風くびれレイヤー髪質改善透明感` (17文字) - 最小限の要素"""
            comment_examples = """- `透けるような透明感のミルクティーグレージュ。ブリーチよりも傷まず、ノンカラーよりも圧倒的に透明感がでるので、現状の髪色が暗めの方、いつもオレンジになってしまう方はこちらがおススメです♪` (92文字)
- `大人気のハイトーンカラー＊綺麗なハイトーンを維持するには2ヶ月半でのリタッチがオススメです＊綺麗なブリーチのベースを作ることで色落ちも気になりにくくなり、ストレスなくハイトーンを続けられます＊ぜひお任せください！` (106文字)
- `気に入ったスタイルは【ブックマーク】をしていただくと便利です！小顔似合わせカットが大人気。20代30代から40代50代まで幅広い年齢層の方にご来店いただいています。お悩みの方はお気軽にご相談ください♪` (100文字)"""
            menu_examples = """- `カット+透明感カラー+髪質改善トリートメント+炭酸スパ+前髪カット込み◎ダメージレスで艶髪に` (46文字)
- `カット+イルミナカラー+TOKIOトリートメント+ヘッドスパ+前髪カット込み◎うる艶カラーで美髪` (48文字)
- `カット+ダブルカラー+ケアブリーチ+カラーシャンプー付き+毛先トリートメント◎透明感ハイトーン` (47文字)"""
            symbol_examples = """- 「◎」: キーワードの強調（例: 小顔◎透明感カラー）
- 「/」: キーワードの並列・区切り（例: レイヤーカット/韓国/前髪カット）
- 「◆」: 装飾・強調（例: 上品韓国ヘア◆グレージュ）
- 「×」: スタイルや色の並列（例: 韓国風×くびれミディ）
- 記号なし: 自然な連結（例: ミディアムレイヤー顔周りカラー韓国ヘア）"""
            hashtag_examples = '- `["髪質改善", "透明感カラー", "艶髪", "ストレートヘア", "トリートメント", "美髪", "サラサラ", "ダメージケア", "美容室", "ヘアスタイル"]`'

        prompt = f"""あなたは日本の{gender_name}美容トレンドに詳しく、魅力的なコピーライティングが得意なマーケターです。
HotPepper Beautyの人気サロンで使用されている、効果的なタイトルやキャッチコピーの特徴を熟知しています。
{featured_instruction}
## 参照データ
以下は、HotPepper Beautyで「{keyword}」と検索して得られた{gender_name}ヘアスタイルタイトルです：

{titles_json}

## 参照データのトレンド分析
まず上記の参照データを分析し、検索キーワード「{keyword}」と頻繁に組み合わされているキーワードやスタイル名を特定してください。
参照データ内で繰り返し登場するキーワードの組み合わせは、現在の人気トレンドを反映しています。

分析結果を出力JSONの「trending_keywords」フィールドに記録し、
その頻出キーワードをテンプレートのタイトルに自然に組み込んでください。
ただし、**文字数制限（タイトル{config.CHAR_LIMITS['title']}文字以内）が常に最優先です。**
文字数を超えてまでキーワードを詰め込む必要はありません。
文字数内に収まる範囲で、頻出キーワードをバランスよく反映してください。

## 生成依頼
上記の参照データとトレンド分析結果を踏まえ、頻出キーワードの組み合わせパターンを自然に反映した新しい魅力的な{gender_name}ヘアスタイルテンプレートを{config.MAX_TEMPLATES}個生成してください。

## 制約条件（優先度順）

### 最重要: 文字数の厳守
各要素は上限を**絶対に超えないでください**。超過したテンプレートは無効になります。上限の少し手前を狙ってください。
{title_length_rule}（上限{config.CHAR_LIMITS['title']}文字。超えたら無効）
- menu: **40〜47文字**を目標（上限{config.CHAR_LIMITS['menu']}文字。超えたら無効）
- comment: **90〜115文字**を目標（上限{config.CHAR_LIMITS['comment']}文字。超えたら無効）
- hashtag: 各ワード{config.CHAR_LIMITS['hashtag']}文字以内、7個以上
{short_title_note}
### 重要: キーワード数の要求
タイトルには必ずキーワード「{keyword}」を含めてください。
**文字数制限内に収まる範囲で**、合計3〜5個程度のキーワードを盛り込んでください。
キーワード数を増やすより、文字数制限を守ることを優先してください。
{keyword_examples}

### 推奨: 表現の質
- **掘り下げキーワード:** 一般的な表現から一歩踏み込み、より具体的な表現を使用してください。
    - 例: 「ショートヘア」→「小顔ショート」「ハンサムショート」、「メンズパーマ」→「スパイラルパーマ」「ツイストパーマ」
- 固有名詞（サロン名、スタイリスト名、商品名、ブランド名）は避け、汎用的な表現を使用してください。

## 各要素の生成ガイドライン
{mens_note}
### 【タイトル】（上限{config.CHAR_LIMITS['title']}文字。目標文字数は「最重要: 文字数の厳守」に従ってください）

**構成パターン（参考）:**
`[印象/願望] + [スタイル/髪型] + [色/技術] + [ターゲット層(任意)]` のような要素を組み合わせるのが基本ですが、**あくまで参考**です。
要素の順番・有無・数は自由に調整してください。**文字数制限を守ることが最優先**なので、構成パターンに縛られて文字数超過するくらいなら、要素を減らして簡潔にまとめてください。

**記号ルール:**
参照データを見ると、上位スタイルでは「◎」「/」「◆」「×」「【】」などの記号が使われたり、記号なしのタイトルも多数あります。
Gemini側で**参照データのスタイルを参考に、自由に記号を選択**してください（記号なしでも構いません）。
以下は使用可能な記号の例です:
{symbol_examples}

**キーワード選定の参考（参照データのトレンド分析結果を優先してください）:**
{title_keyword_hints}

**ターゲット層:**
「20代30代」「30代40代」など年代を入れると検索に効果的ですが、**{config.MAX_TEMPLATES}個中{config.MAX_TEMPLATES // 2}個程度**に留めてください。残りには年代を入れず、スタイルや技術で差別化してください。

**具体性:**
{specificity_hint}

**良いタイトル例（記号の使い方のバリエーション）:**
{title_examples}

※記号なしや少ない記号でも十分に魅力的なタイトルになります。文字数オーバーするくらいなら要素を減らしてください。

### 【メニュー】（40〜47文字、上限{config.CHAR_LIMITS['menu']}文字）
- 具体的な施術内容をすべて含める（カット、カラー、トリートメントなど）
- 付加価値のある組み合わせを提案（○○込み、○○無料など）
- オプションやケアアイテム、特別なテクニックも含める
- トレンド感のある施術名を使用し、価格やお得感を表現

**良いメニュー例（40〜47文字）:**
{menu_examples}

### 【コメント】（90〜115文字、上限{config.CHAR_LIMITS['comment']}文字）
- 施術による具体的な効果や変化を詳しく説明
- お客様の悩みに対する解決策を提示
- 施術後のイメージを魅力的に描写
- トレンドに合わせたアピールポイントを含める

**良いコメント例（90〜115文字）:**
{comment_examples}

### 【ハッシュタグ】（各{config.CHAR_LIMITS['hashtag']}文字以内、7個以上）
- トレンドのキーワード、施術内容、検索されやすい一般タグを網羅
- スタイルの特徴を表すタグも含める
- `#` は含めず、文字列の配列（リスト）として生成してください

**良いハッシュタグ例（7〜10個）:**
{hashtag_examples}

## 出力形式
結果は以下のJSON形式で出力してください。trending_keywordsを先に出力し、その分析結果を反映したtemplatesを生成してください:

{{
  "trending_keywords": [
    {{"keyword": "キーワード名", "count": 出現数, "reason": "参照データN件中M件に出現"}}
  ],
  "templates": [
    {{
      "title": "【タイトル】",
      "menu": "【メニュー】",
      "comment": "【コメント】",
      "hashtag": ["ハッシュタグ1", "ハッシュタグ2", ... ]
    }}
  ]
}}
"""
        logger.debug(f"プロンプト作成: 入力タイトル数: {len(titles)}, キーワード: '{keyword}', 季節・カラー選択: {selected_seasons}, 性別: '{gender}'")
        return prompt
        
    def _parse_response(self, response_text: str) -> Tuple[List[Dict], List[Dict]]:
        """Gemini APIレスポンスからテンプレートとトレンドキーワードを抽出する

        新形式（オブジェクト {trending_keywords, templates}）を優先し、
        失敗時は旧形式（配列 [templates]）にフォールバックする。

        Args:
            response_text: Gemini APIから受信した生のレスポンステキスト

        Returns:
            (templates, trending_keywords) のタプル。
            templates: テンプレート辞書のリスト
            trending_keywords: トレンドキーワード辞書のリスト（旧形式時は空リスト）

        Raises:
            ValueError: 有効なJSONレスポンスが見つからない場合
        """
        # マークダウンのコードブロックを除去
        code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', response_text, re.DOTALL)
        if code_block_match:
            json_text = code_block_match.group(1).strip()
            logger.debug("マークダウンコードブロックからJSONを抽出")
        else:
            json_text = response_text

        trending_keywords: List[Dict] = []

        # JSONの外側の構造を判別する: 先に出現する '{' と '[' のどちらかを外側の構造とみなす。
        # これにより、配列内のオブジェクト {...} や オブジェクト内の配列 [...] を
        # 誤って外側の構造と判定するバグを防ぐ。
        first_brace = json_text.find('{')
        first_bracket = json_text.find('[')

        is_object_outer = (
            first_brace != -1
            and (first_bracket == -1 or first_brace < first_bracket)
        )
        is_array_outer = (
            first_bracket != -1
            and (first_brace == -1 or first_bracket < first_brace)
        )

        # 新形式: オブジェクト形式 {trending_keywords: [...], templates: [...]} を試行
        if is_object_outer:
            end_obj = json_text.rfind('}')
            if end_obj > first_brace:
                try:
                    parsed = json.loads(json_text[first_brace:end_obj + 1])
                    if isinstance(parsed, dict):
                        templates = parsed.get('templates')
                        if isinstance(templates, list):
                            trending_keywords = parsed.get('trending_keywords', []) or []
                            if trending_keywords:
                                logger.info(f"トレンドキーワード分析結果: {json.dumps(trending_keywords, ensure_ascii=False)}")
                            logger.info("新形式（オブジェクト）でパース成功")
                            return templates, trending_keywords
                        # オブジェクトだが templates キーが無い/不正 - エラー
                        # （配列フォールバックに落とすと内部の [] を誤って拾うバグの原因になる）
                        raise ValueError("JSONオブジェクトに有効な'templates'リストがありません")
                except json.JSONDecodeError:
                    logger.debug("オブジェクト形式のJSONパースに失敗")

        # 旧形式: 配列形式 [...] を試行
        if is_array_outer:
            end = json_text.rfind(']')
            if end > first_bracket:
                try:
                    templates = json.loads(json_text[first_bracket:end + 1])
                    if isinstance(templates, list):
                        logger.info("旧形式（配列）でパース成功")
                        return templates, trending_keywords
                except json.JSONDecodeError:
                    pass

        raise ValueError("Invalid JSON response from Gemini API: No valid JSON found")

    def _validate_template(self, template: Dict[str, str], keyword: str) -> bool:
        """テンプレートの文字数制限チェックとキーワード含有チェック"""
        try:
            # 必須キーの存在チェック
            required_keys = ['title', 'menu', 'comment', 'hashtag']
            for key in required_keys:
                if key not in template:
                    logger.warning(f"テンプレートに必須キー '{key}' がありません")
                    return False
            
            # タイトルにキーワードが含まれているかチェック（警告のみ出力し、テンプレートは有効とする）
            if keyword.lower() not in template['title'].lower():
                logger.warning(f"タイトルにキーワード '{keyword}' が含まれていません: {template['title']}")
                # キーワードが含まれていなくても、テンプレートを有効とする（return Falseを削除）
                
            # 文字数制限チェック
            for key, limit in config.CHAR_LIMITS.items():
                if key == 'hashtag':
                    # ハッシュタグは配列なのでスキップ
                    continue
                    
                if len(template[key]) > limit:
                    logger.warning(f"{key}の文字数が制限を超えています: {len(template[key])} > {limit}")
                    return False
            
            # ハッシュタグのチェック
            if not isinstance(template['hashtag'], list):
                logger.warning(f"ハッシュタグがリスト形式ではありません: {type(template['hashtag'])}")
                return False
                
            if len(template['hashtag']) < 7:
                logger.warning(f"ハッシュタグの数が少なすぎます: {len(template['hashtag'])} < 7")
                return False
                
            for tag in template['hashtag']:
                if len(tag) > config.CHAR_LIMITS['hashtag']:
                    logger.warning(f"ハッシュタグが長すぎます: {tag} ({len(tag)} > {config.CHAR_LIMITS['hashtag']})")
                    return False
            
            logger.debug(f"テンプレート検証成功: '{template['title']}'")
            return True
        except (KeyError, AttributeError) as e:
            logger.error(f"テンプレート検証エラー: {str(e)}")
            return False

    @staticmethod
    def _pick_separator(title: str, rotation_index: int) -> Tuple[str, int]:
        """タイトルに付ける区切り記号と、次のローテーション位置を返す"""
        # タイトルがすでに使っている区切り記号に合わせる（複数あれば末尾に近いもの）
        matched = max(
            (d for d in config.SEASON_APPEND_DELIMITERS if d in title),
            key=title.rfind,
            default=None
        )
        if matched is not None:
            return matched, rotation_index

        # 記号なしのタイトルには記号を順番に割り当てる（すでに含む記号は避ける）
        rotation = config.SEASON_APPEND_SEPARATORS
        separator = rotation[rotation_index % len(rotation)]
        for _ in range(len(rotation)):
            separator = rotation[rotation_index % len(rotation)]
            rotation_index += 1
            if separator not in title:
                break
        return separator, rotation_index

    def _apply_season_keywords(self, templates: List[Dict[str, str]], seasons: List[str]) -> None:
        """選択された季節・カラーキーワードをタイトルへ付加する（テンプレートを直接書き換える）

        - SEASON_APPEND_THRESHOLD 文字未満のタイトルのみが対象
        - 付加後に上限文字数を超える場合は付加しない
        - 複数選択時は対象タイトルへ均等に配分する
        - 各キーワードには、収まる範囲で最も長いタイトル＝上限文字数に最も近づくものを割り当てる
        - 区切り記号はタイトルが使っている記号に合わせ、記号がなければローテーションする
        """
        if not seasons or not templates:
            return

        # 重複があると割り当てループのキーワード集合が空になりうるため、ここでも重複を除く
        seasons = list(dict.fromkeys(seasons))

        title_limit = config.CHAR_LIMITS['title']
        # 区切り記号は全て1文字だが、将来増えても破綻しないよう最長で見積もる
        separator_length = max(
            len(s) for s in config.SEASON_APPEND_SEPARATORS + config.SEASON_APPEND_DELIMITERS
        )
        keywords = {key: config.SEASON_COLOR_CHOICES[key] for key in seasons}
        counts = {key: 0 for key in seasons}
        priority = {key: i for i, key in enumerate(seasons)}
        rotation_index = 0

        # 付加対象を長い順に並べる。キーワードごとに「収まる中で最も長いタイトル」を取れるようにするため
        remaining = sorted(
            (t for t in templates if len(t.get('title', '')) < config.SEASON_APPEND_THRESHOLD),
            key=lambda t: len(t.get('title', '')),
            reverse=True
        )

        # タイトル側ではなくキーワード側から割り当てる。
        # 付加済み件数が最少のキーワードから順に処理することで均等配分になり、
        # かつ各キーワードが上限文字数に最も近づくタイトルを選べる
        exhausted = set()
        while remaining and len(exhausted) < len(seasons):
            key = min(
                (k for k in seasons if k not in exhausted),
                key=lambda k: (counts[k], priority[k])
            )
            keyword = keywords[key]
            target = next(
                (t for t in remaining
                 if keyword not in t['title']
                 and len(t['title']) + separator_length + len(keyword) <= title_limit),
                None
            )
            if target is None:
                # このキーワードを付加できるタイトルはもう残っていない
                exhausted.add(key)
                continue

            remaining.remove(target)
            separator, rotation_index = self._pick_separator(target['title'], rotation_index)
            target['title'] = f"{target['title']}{separator}{keyword}"
            counts[key] += 1

        applied = sum(counts.values())
        logger.info(f"季節・カラーキーワードを {applied} 件のタイトルに付加しました: {counts}")

    async def generate_templates_async(self, titles: List[str], keyword: str, seasons: List[str] = None, gender: str = 'ladies', featured_info: Dict = None, generation_context: Dict = None) -> Tuple[List[Dict[str, str]], List[Dict]]:
        """テンプレートの非同期生成

        Returns:
            (valid_templates, trending_keywords) のタプル
        """
        # 入力検証を追加
        if not titles:
            logger.error("タイトルリストが空です")
            raise ValueError("タイトルリストが空です")
        if not keyword:
            logger.error("キーワードが指定されていません")
            raise ValueError("キーワードが指定されていません")
            
        # 生成コンテキストの処理
        context = generation_context or {}
        keyword_type = context.get('keyword_type', 'normal')
        processing_mode = context.get('processing_mode', 'standard')
        
        selected_seasons = self._normalize_seasons(seasons, gender)

        logger.info(f"非同期テンプレート生成開始: タイトル数: {len(titles)}, キーワード: '{keyword}', 季節・カラー選択: {selected_seasons}, 性別: '{gender}', 特集対応: {featured_info is not None}, キーワードタイプ: {keyword_type}, 処理モード: {processing_mode}")
        prompt = self._create_prompt(titles, keyword, selected_seasons, gender, featured_info, generation_context)
        
        try:
            logger.debug(f"生成されたプロンプト全体:\n{prompt}")
            logger.info("Gemini APIリクエスト送信中（thinkingLevel=MINIMAL）...")

            config_with_thinking = types.GenerateContentConfig(
                temperature=1.0,
                max_output_tokens=32768,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.MINIMAL  # 高速化のため思考プロセスを最小化
                )
            )
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config_with_thinking
            )
            response_text = response.text
            logger.info("Gemini API応答受信（thinkingLevel=MINIMAL）")
            logger.debug(f"Gemini APIレスポンス受信: 文字数 {len(response_text)}")
            
            # JSON文字列の抽出とパース
            try:
                templates, trending_keywords = self._parse_response(response_text)
                logger.info(f"APIから {len(templates)} 件のテンプレートを受信")
            except (ValueError, json.JSONDecodeError) as e:
                logger.error(f"JSONパースエラー: {str(e)}")
                logger.debug(f"エラーが発生したレスポンスの一部: {response_text[:200]}...")
                raise ValueError(f"Invalid JSON response from Gemini API: {str(e)}")
            
            # バリデーション
            valid_templates = []
            for i, template in enumerate(templates):
                logger.debug(f"テンプレート {i+1} の検証: {template.get('title', '不明')}")
                if self._validate_template(template, keyword):
                    valid_templates.append(template)
                else:
                    logger.warning(f"テンプレート {i+1} は検証に失敗しました")
            
            if not valid_templates:
                logger.error("有効なテンプレートがありません")
                raise ValueError("No valid templates generated")
                
            result_templates = valid_templates[:config.MAX_TEMPLATES]

            # 選択された季節・カラーキーワードを後処理で付加する
            self._apply_season_keywords(result_templates, selected_seasons)

            logger.info(f"テンプレート生成完了: {len(result_templates)} 件の有効なテンプレート")
            return result_templates, trending_keywords
            
        except Exception as e:
            if isinstance(e, ValueError):
                logger.error(f"テンプレート生成エラー (ValueError): {str(e)}")
                raise e
            logger.error(f"テンプレート生成エラー: {str(e)}")
            raise Exception(f"Template generation failed: {str(e)}")
        
    def generate_templates(self, titles: List[str], keyword: str, seasons: List[str] = None, gender: str = 'ladies', featured_info: Dict = None, generation_context: Dict = None) -> Tuple[List[Dict[str, str]], List[Dict]]:
        """テンプレートの生成（同期版ラッパー）"""
        context = generation_context or {}
        logger.info(f"同期版 generate_templates が呼び出されました - キーワード: '{keyword}', 季節・カラー選択: {seasons}, 性別: '{gender}', 特集対応: {featured_info is not None}, コンテキスト: {context.get('keyword_type', 'normal')} - 内部で非同期処理を実行します")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.generate_templates_async(titles, keyword, seasons, gender, featured_info, generation_context))
        finally:
            loop.close()