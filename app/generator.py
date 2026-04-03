from google import genai
from google.genai import types
from typing import List, Dict
import json
import logging
import asyncio
from . import config

# ロガーの設定
logger = logging.getLogger(__name__)

class TemplateGenerator:
    def __init__(self, model_name='gemini-3-flash-preview'):
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")

        # サポートされているモデルの検証
        supported_models = ['gemini-3-flash-preview', 'gemini-3.1-flash-lite-preview']
        if model_name not in supported_models:
            logger.warning(f"Unsupported model: {model_name}, falling back to gemini-3-flash-preview")
            model_name = 'gemini-3-flash-preview'

        self.model_name = model_name

        # Google GenAI SDKクライアント初期化
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        logger.info(f"TemplateGeneratorが初期化されました（モデル: {model_name}）")
        
    def _create_prompt(self, titles: List[str], keyword: str, season: str = None, gender: str = 'ladies', featured_info: Dict = None, generation_context: Dict = None) -> str:
        """プロンプトテンプレートの作成"""
        titles_json = json.dumps(titles, ensure_ascii=False, indent=2)
        
        # 性別に応じた設定
        gender_name = "レディース" if gender == 'ladies' else "メンズ"
        
        season_intro = ""
        season_instruction = ""
        season_specific_keywords_prompt = ""

        if season and season != "none" and season in config.SEASON_KEYWORDS:
            season_name = season # UIから渡される値が日本語名でない場合、ここで変換が必要かも
            # 実際のUIからの値に合わせて調整してください (例: "spring" -> "春")
            # ここでは簡単のため、キーをそのまま表示名として扱います
            if season == "spring": season_name = "春"
            elif season == "summer": season_name = "夏"
            elif season == "autumn": season_name = "秋"
            elif season == "winter": season_name = "冬"
            elif season == "all_year": season_name = "通年"
            elif season == "graduation_entrance": season_name = "卒業・入学シーズン"
            elif season == "rainy_season": season_name = "梅雨"
            elif season == "year_end_new_year": season_name = "年末年始・成人式"
            
            season_intro = f"\n特に、ユーザーは「{season_name}」のシーズンに関心があります。これを最優先で考慮してください。\n"
            season_instruction = f"""
- **シーズン対応:**
    - ユーザー指定の「{season_name}」を強く意識し、タイトル、メニュー、コメント、ハッシュタグの全てにその季節感やイベントの雰囲気を反映させてください。
    - 例えば、「{season_name}」であれば、{config.SEASON_KEYWORDS.get(season, [])} のようなキーワードや表現が考えられます。これらを参考に、自然で魅力的な形で盛り込んでください。
    - タイトルに含める5つ以上のキーワードのうち、1つ以上は必ずこの「{season_name}」に関連するキーワードにしてください。
"""
            if config.SEASON_KEYWORDS.get(season):
                 season_specific_keywords_prompt = f"\nまた、「{season_name}」に関連するキーワードとして、例えば以下のようなものが挙げられます。これらも参考にしてください：\n`{', '.join(config.SEASON_KEYWORDS.get(season, []))}`\n"
        else:
            season_instruction = f"""
- **シーズン対応:**
    - 特定のシーズン指定はありませんが、もし可能であれば、美容トレンドに合ったシーズンワードを適宜取り入れてください。必須ではありません。
"""

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

        # PV向上キーワード指示（常に適用）
        pv_instruction = ""
        pv_keywords = config.PV_BOOST_KEYWORDS
        pv_count = config.PV_BOOST_COUNT_PER_KEYWORD
        if pv_keywords and pv_count > 0:
            pv_keyword_rules = "\n".join(
                f"- 「{kw}」→ タイトル{i * pv_count + 1}番目と{i * pv_count + 2}番目に含める"
                for i, kw in enumerate(pv_keywords)
            )
            pv_total = len(pv_keywords) * pv_count
            pv_instruction = f"""
**【重要】PV向上キーワードの配置ルール:**
以下の{len(pv_keywords)}つのPV向上キーワードを、生成する{config.MAX_TEMPLATES}個のタイトルに必ず均等に配置してください。
各キーワードはちょうど{pv_count}個のタイトルに含めてください（合計{pv_total}個のタイトルにPV向上キーワードが入ります）。

配置ルール:
{pv_keyword_rules}

※ 残りのタイトル（{pv_total + 1}番目〜{config.MAX_TEMPLATES}番目）にはPV向上キーワードを含めなくても構いません。
※ このルールはユーザーの検索キーワード、シーズン選択、性別に関係なく、常に適用してください。
※ PV向上キーワードはタイトルの「5つ以上のキーワード」の1つとしてカウントしてください。
"""
            logger.debug(f"PV向上キーワード {len(pv_keywords)}個を配置ルールとしてプロンプトに追加")

        # メンズ固有の注意点（メンズの場合のみ）
        mens_note = ""
        if gender == 'mens':
            mens_note = """
- **メンズ特有キーワードの活用:**
    - ターゲット層: メンズ、20代30代、社会人、学生
    - スタイル: ツーブロック、センターパート、フェード、マッシュ、ショート
    - 技術: パーマ、ツイスパ、ニュアンスパーマ、波巻きパーマ
    - 効果: 小顔効果、骨格補正、清潔感、爽やか
    - 用途: ビジネス、カジュアル、オフィス
    - トレンド: 韓国風、外国人風、モダン
"""

        prompt = f"""あなたは日本の{gender_name}美容トレンドに詳しく、魅力的なコピーライティングが得意なマーケターです。
HotPepper Beautyの人気サロンで使用されている、効果的なタイトルやキャッチコピーの特徴を熟知しています。
{season_intro}{featured_instruction}
## 参照データ
以下は、HotPepper Beautyで「{keyword}」と検索して得られた{gender_name}ヘアスタイルタイトルです：

{titles_json}

## 生成依頼
上記リストとキーワード「{keyword}」を参考に、最新トレンドを反映した新しい魅力的な{gender_name}ヘアスタイルテンプレートを{config.MAX_TEMPLATES}個生成してください。

## 制約条件（優先度順）

### 最重要: 文字数の厳守
各要素は上限を**絶対に超えないでください**。超過したテンプレートは無効になります。上限の少し手前を狙ってください。
- title: **25〜28文字**を目標（上限{config.CHAR_LIMITS['title']}文字。超えたら無効）
- menu: **40〜47文字**を目標（上限{config.CHAR_LIMITS['menu']}文字。超えたら無効）
- comment: **90〜115文字**を目標（上限{config.CHAR_LIMITS['comment']}文字。超えたら無効）
- hashtag: 各ワード{config.CHAR_LIMITS['hashtag']}文字以内、7個以上

### 重要: キーワード数の要求
タイトルには必ずキーワード「{keyword}」を含め、合計で**5つ以上**のキーワードを盛り込んでください。
（例: ブリーチなし / ダブルカラー / 20代30代 / 春カラー / 透明感 / 小顔効果 / 韓国風）

{pv_instruction}

### 推奨: 表現の質
- **掘り下げキーワード:** 一般的な表現から一歩踏み込み、より具体的な表現を使用してください。
    - 例: 「ショートヘア」→「小顔ショート」「ハンサムショート」、「メンズパーマ」→「スパイラルパーマ」「ツイストパーマ」
- 固有名詞（サロン名、スタイリスト名、商品名、ブランド名）は避け、汎用的な表現を使用してください。
{season_specific_keywords_prompt}
## 各要素の生成ガイドライン
{season_instruction}{mens_note}
### 【タイトル】（25〜28文字、上限{config.CHAR_LIMITS['title']}文字）

**構成パターン:**
`[印象/願望] + [スタイル/髪型] + [◎強調キーワード] + [色/技術] + [ターゲット層(任意)]`
※要素の順番は柔軟に変更可能です。

**記号ルール:**
- 強調したいキーワードには「◎」を使用（例: 小顔◎透明感カラー）
- 複数のスタイル名や色名の並列には「×」を使用（例: 韓国風×くびれミディ）

**キーワード選定の参考:**
`大人可愛い`, `小顔`, `美髪`, `艶髪`, `透明感`, `似合わせ`, `イメチェン`, `レイヤー`, `ウルフ`, `くびれ`, `韓国風`, `シースルーバング`, `髪質改善`, `暗髪`, `インナーカラー`, `ハイライト`, `バレイヤージュ`, `縮毛矯正`, `デジタルパーマ` など

**ターゲット層:**
「20代30代」「30代40代」など年代を入れると検索に効果的ですが、**{config.MAX_TEMPLATES}個中{config.MAX_TEMPLATES // 2}個程度**に留めてください。残りには年代を入れず、スタイルや技術で差別化してください。

**具体性:**
髪型（ボブ, ミディアム, ロング, ショート, ウルフ, レイヤー）、色（アッシュ, ベージュ, グレージュ, ピンク, ラベンダー）、技術（カット, カラー, パーマ, トリートメント, ハイライト, ブリーチ）を複数組み合わせてください。

**良いタイトル例（25〜28文字）:**

レディース:
- `大人可愛い透明感グレージュ◎20代30代美人ヘア` (24文字)
    → 印象 + 色 + 記号 + ターゲット層 + 付加価値
- `小顔◎韓国風ブリーチなしカラー透明感アッシュ` (22文字)
    → 願望 + 記号 + スタイル + 技術 + 色（年代なし）
- `30代40代◎くびれミディ×艶髪ラベンダーカラー` (24文字)
    → ターゲット層 + 記号 + スタイル + 印象 + 色

メンズ:
- `小顔効果◎メンズパーマ波巻き×センターパート` (22文字)
    → 効果 + 記号 + 技術 + スタイル（年代なし）
- `ビジネス◎ツイスパ×センターパート×ニュアンスパーマ` (26文字)
    → 用途 + 記号 + 技術 + スタイル（年代なし）
- `20代30代◎韓国風マッシュ×ニュアンスパーマ爽やか` (26文字)
    → ターゲット層 + トレンド + スタイル + 技術 + 印象

### 【メニュー】（40〜47文字、上限{config.CHAR_LIMITS['menu']}文字）
- 具体的な施術内容をすべて含める（カット、カラー、トリートメントなど）
- 付加価値のある組み合わせを提案（○○込み、○○無料など）
- オプションやケアアイテム、特別なテクニックも含める
- トレンド感のある施術名を使用し、価格やお得感を表現

**良いメニュー例（40〜47文字）:**
- `カット+透明感カラー+髪質改善トリートメント+炭酸スパ+前髪カット込み◎ダメージレスで艶髪に` (46文字)
- `カット+イルミナカラー+TOKIOトリートメント+ヘッドスパ+前髪カット込み◎うる艶カラーで美髪` (48文字)
- `カット+ダブルカラー+ケアブリーチ+カラーシャンプー付き+毛先トリートメント◎透明感ハイトーン` (47文字)

### 【コメント】（90〜115文字、上限{config.CHAR_LIMITS['comment']}文字）
- 施術による具体的な効果や変化を詳しく説明
- お客様の悩みに対する解決策を提示
- 施術後のイメージを魅力的に描写
- 季節やトレンドに合わせたアピールポイントを含める

**良いコメント例（90〜115文字）:**

レディース:
- `透けるような透明感のミルクティーグレージュ。ブリーチよりも傷まず、ノンカラーよりも圧倒的に透明感がでるので、現状の髪色が暗めの方、いつもオレンジになってしまう方はこちらがおススメです♪` (92文字)
- `大人気のハイトーンカラー＊綺麗なハイトーンを維持するには2ヶ月半でのリタッチがオススメです＊綺麗なブリーチのベースを作ることで色落ちも気になりにくくなり、ストレスなくハイトーンを続けられます＊ぜひお任せください！` (106文字)
- `気に入ったスタイルは【ブックマーク】をしていただくと便利です！小顔似合わせカットが大人気。20代30代から40代50代まで幅広い年齢層の方にご来店いただいています。お悩みの方はお気軽にご相談ください♪` (100文字)

メンズ:
- `頭の形が綺麗に見えるよう常に意識をしています！パーマをかけることでより骨格補正効果、スタイリングも簡単！学生はもちろん、社会人の方にもオススメ！黒髪相性良し！誰もが悩む絶壁、ハチ張り一緒に解消しましょう！` (102文字)
- `ツイストスパイラルパーマで今一番かっこいい髪型です♪ツイスパならではの動きを質感でだしつつ、やり過ぎない動きに仕上げました。ナチュラルでも、ウェットでも、ドライでも質感の好みやその日の気分で雰囲気を変えてもかっこよくキマります☆` (114文字)
- `マッシュショートの爽やかスタイル！時間のない朝にも時短でできる朝ラクヘア！10代から20代、30代から40代、50代と幅広く人気の王道スタイルです！外国人風の奥行きと骨格補正で似合わせバツグン！` (97文字)

### 【ハッシュタグ】（各{config.CHAR_LIMITS['hashtag']}文字以内、7個以上）
- トレンドのキーワード、施術内容、検索されやすい一般タグを網羅
- 季節やイベント関連、スタイルの特徴を表すタグも含める
- `#` は含めず、文字列の配列（リスト）として生成してください

**良いハッシュタグ例（7〜10個）:**
- `["髪質改善", "透明感カラー", "艶髪", "ストレートヘア", "トリートメント", "美髪", "サラサラ", "ダメージケア", "美容室", "ヘアスタイル"]`
- `["韓国風", "マッシュ", "ニュアンスパーマ", "無造作", "メンズヘア", "おしゃれ", "トレンド", "ヘアスタイル", "美容院", "カット"]`

## 出力形式
結果は以下のJSON形式で出力してください:

[
  {{
    "title": "【タイトル】",
    "menu": "【メニュー】",
    "comment": "【コメント】",
    "hashtag": ["ハッシュタグ1", "ハッシュタグ2", ... ]
  }},
  ...
]
"""
        logger.debug(f"プロンプト作成: 入力タイトル数: {len(titles)}, キーワード: '{keyword}', シーズン: '{season}', 性別: '{gender}'")
        return prompt
        
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
    
    async def generate_templates_async(self, titles: List[str], keyword: str, season: str = None, gender: str = 'ladies', featured_info: Dict = None, generation_context: Dict = None) -> List[Dict[str, str]]:
        """テンプレートの非同期生成"""
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
        
        logger.info(f"非同期テンプレート生成開始: タイトル数: {len(titles)}, キーワード: '{keyword}', シーズン: '{season}', 性別: '{gender}', 特集対応: {featured_info is not None}, キーワードタイプ: {keyword_type}, 処理モード: {processing_mode}")
        prompt = self._create_prompt(titles, keyword, season, gender, featured_info, generation_context)
        
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
            
            # JSON文字列の抽出（レスポンスにマークダウンなどが含まれている可能性があるため）
            try:
                start = response_text.find('[')
                if start == -1:
                    logger.error("Gemini APIレスポンスから開始ブラケット '[' が見つかりません")
                    raise ValueError("Invalid JSON response from Gemini API: Missing opening bracket")
                    
                end = response_text.rfind(']')
                if end == -1:
                    logger.error("Gemini APIレスポンスから終了ブラケット ']' が見つかりません")
                    raise ValueError("Invalid JSON response from Gemini API: Missing closing bracket")
                    
                json_str = response_text[start:end + 1]
                templates = json.loads(json_str)
                
                if not isinstance(templates, list):
                    logger.error(f"無効なJSONレスポンス: リスト形式ではありません (型: {type(templates)})")
                    raise ValueError("Invalid JSON response from Gemini API: Not a list")
                    
                logger.info(f"APIから {len(templates)} 件のテンプレートを受信")
                
            except (ValueError, json.JSONDecodeError) as e:
                logger.error(f"JSONパースエラー: {str(e)}")
                # エラーが発生した場合はレスポンスの一部をログに出力
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
                
            logger.info(f"テンプレート生成完了: {len(valid_templates)} 件の有効なテンプレート")
            return valid_templates[:config.MAX_TEMPLATES]
            
        except Exception as e:
            if isinstance(e, ValueError):
                logger.error(f"テンプレート生成エラー (ValueError): {str(e)}")
                raise e
            logger.error(f"テンプレート生成エラー: {str(e)}")
            raise Exception(f"Template generation failed: {str(e)}")
        
    def generate_templates(self, titles: List[str], keyword: str, season: str = None, gender: str = 'ladies', featured_info: Dict = None, generation_context: Dict = None) -> List[Dict[str, str]]:
        """テンプレートの生成（同期版ラッパー）"""
        context = generation_context or {}
        logger.info(f"同期版 generate_templates が呼び出されました - キーワード: '{keyword}', シーズン: '{season}', 性別: '{gender}', 特集対応: {featured_info is not None}, コンテキスト: {context.get('keyword_type', 'normal')} - 内部で非同期処理を実行します")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.generate_templates_async(titles, keyword, season, gender, featured_info, generation_context))
        finally:
            loop.close()