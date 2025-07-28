import google.generativeai as genai
from google import genai as new_genai
from google.genai import types
from typing import List, Dict, Optional
import json
import logging
import asyncio
from . import config

# ロガーの設定
logger = logging.getLogger(__name__)

class TemplateGenerator:
    def __init__(self, model_name='gemini-2.5-flash'):
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")
        
        # サポートされているモデルの検証
        supported_models = ['gemini-2.5-flash', 'gemini-2.5-flash-lite']
        if model_name not in supported_models:
            logger.warning(f"Unsupported model: {model_name}, falling back to gemini-2.5-flash")
            model_name = 'gemini-2.5-flash'
        
        self.model_name = model_name
        
        # 新しいSDKのクライアント初期化
        self.client = new_genai.Client(api_key=config.GEMINI_API_KEY)
        # 旧SDKとの互換性のため
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"TemplateGeneratorが初期化されました（新SDK対応、モデル: {model_name}）")
        
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

        prompt = f"""
あなたは日本の{gender_name}美容トレンドに詳しく、魅力的なコピーライティングが得意なマーケターです。
HotPepper Beautyの人気サロンで使用されている、効果的なタイトルやキャッチコピーの特徴を熟知しています。
{season_intro}{featured_instruction}
以下の{gender_name}ヘアスタイルタイトルリストは、HotPepper Beautyで「{keyword}」というキーワードで検索して得られた結果です：

{titles_json}


上記リストとキーワード「{keyword}」を参考に、最新トレンドを反映した、新しい魅力的な{gender_name}ヘアスタイルタイトル案を{config.MAX_TEMPLATES}つ生成してください。

**【最重要】キーワード数の厳格な要求:**
タイトルには必ずキーワード「{keyword}」を含め、合計で**必ず5つ以上**のキーワードを盛り込んでください。
(例:ブリーチなし/ダブルカラー/初カラー/20代30代40代/春カラー/透明感/小顔効果/韓国風)

**特にメンズの場合の注意点:**
メンズ向けタイトルでも必ず5つ以上のキーワードを含めてください。メンズ特有のキーワード例：
- ターゲット層: メンズ、20代30代、社会人、学生
- スタイル: ツーブロック、センターパート、フェード、マッシュ、ショート
- 技術: パーマ、ツイスパ、ニュアンスパーマ、波巻きパーマ
- 効果: 小顔効果、骨格補正、清潔感、爽やか
- 用途: ビジネス、カジュアル、オフィス
- トレンド: 韓国風、外国人風、モダン

これにより検索露出を最大化し、より多くのユーザーにアピールできます。

多くのキーワードを盛り込むことは重要ですが、同時に指定された文字数制限も厳守してください。

**掘り下げキーワードの活用:** 提供されたリストや一般的な表現から一歩踏み込み、スタイルや技術をより具体的に表現する『掘り下げキーワード』を積極的に使用してください。例えば、『ショートヘア』だけでなく『小顔ショート』『ハンサムショート』、『メンズパーマ』だけでなく『スパイラルパーマ』や『ツイストパーマ』のように、より専門的で顧客の具体的なイメージを喚起する言葉を選びましょう。これにより、他の一般的なタイトルとの差別化を図り、顧客の検索意図により合致した提案が可能になります。
{season_specific_keywords_prompt}
各要素の生成ガイドライン：
{season_instruction}
**良いタイトル例:**
以下は、魅力的で情報量が多いと考えられるタイトル例です。これらの例を参考に、構成、キーワードの選択、記号の使い方などを考慮してください。

**レディース例:**
*   `大人可愛い透明感グレージュ◎20代30代40代美人ヘアくすみベージュ`
    *   ポイント: 印象(大人可愛い, 透明感)、色(グレージュ, くすみベージュ)、強調記号◎、ターゲット層(20代30代40代)、付加価値(美人ヘア)
*   `春色ピンクベージュで差をつける◎20代30代向け小顔見せ丸みショートボブ`
    *   ポイント: シーズンワード(春色)、色(ピンクベージュ)、強調記号◎、ターゲット層(20代30代)、掘り下げキーワード(小顔見せ, 丸みショートボブ)
*   `★20代30代小顔韓国ヘア◎ブリーチなし アッシュブラック 大人美人`
    *   ポイント: ターゲット層(20代30代)、願望(小顔)、スタイル(韓国ヘア)、強調記号◎、技術(ブリーチなし)、色(アッシュブラック)、印象(大人美人)
*   `★くびれボブ ミニウルフ◎透明感シルバーアッシュグレージュ ハイトーン`
    *   ポイント: スタイル(くびれボブ, ミニウルフ)、強調記号◎、印象(透明感)、色(シルバーアッシュグレージュ)、技術(ハイトーン)

**メンズ例:**
*   `大人カッコイイ春メンズソフトツーブロックビジネス清潔感`
    *   ポイント: 印象(大人カッコイイ)、シーズンワード(春)、ターゲット層(メンズ)、スタイル(ソフトツーブロック)、用途(ビジネス)、印象(清潔感)
*   `小顔効果◎メンズパーマ波巻きパーマ×センターパート韓国風`
    *   ポイント: 効果(小顔効果)、強調記号◎、ターゲット層(メンズ)、技術(パーマ)、掘り下げキーワード(波巻きパーマ)、並列記号×、スタイル(センターパート)、トレンド(韓国風)
*   `ビジネス◎ツイスパ×センターパート×ニュアンスパーマで好印象`
    *   ポイント: 用途(ビジネス)、強調記号◎、技術(ツイスパ)、並列記号×、スタイル(センターパート)、技術(ニュアンスパーマ)、効果(好印象)

**【タイトル】(ちょうど{config.CHAR_LIMITS['title']}文字に近づける)**
- **構成:** 上記の良い例を参考に、「`[年代/ターゲット層(任意)] + [シーズンワード(任意)] + [印象/願望(複数可)] + [髪型/スタイル(複数可)] + [◎強調キーワード(任意)] + [色/技術(複数可)]`」のような、**情報量が多く魅力的な順序**を意識してください。要素の順番は柔軟に変更可能です。
- **記号:**
    - 特に強調したいキーワードには「◎」を使用してください。（例: ★30代40代◎美髪改善トリートメント付きボブ）
    - 複数のスタイル名や色名を並列する場合は「×」を使用してください。（例: ★韓国風×くびれミディ）
- **キーワード:**
    - 上記の良い例や、以下の頻出キーワードリストを参考に、元のタイトルの内容や文脈に合わせて、**積極的に多くのキーワードを追加・調整**してください。指定されたシーズンがある場合は、それに関連するキーワードも必ず含めてください。:\n        `大人可愛い`, `小顔`, `美髪`, `艶髪`, `透明感`, `似合わせ`, `イメチェン`, `レイヤー`, `ウルフ`, `くびれ`, `韓国風`, `シースルーバング`, `ワイドバング`, `髪質改善`, `暗髪`, `暖色カラー`, `寒色カラー`, `インナーカラー`, `ハイライト`, `バレイヤージュ`, `縮毛矯正`, `デジタルパーマ` ...など
- **ターゲット層:**
    - 上記の良い例のように、「20代30代」「30代40代」「40代50代」など、具体的な年代・ターゲット層を**可能な限り多くの場合で明示**してください。
- **表現:**
    - 検索されやすく、ユーザーの目を引くような言葉を選んでください。
    - 元のタイトルで意味が重複している部分や、効果的でないと思われる表現は整理し、**冗長にならないように**してください。
- **具体性:**
    - 髪型（ボブ, ミディアム, ロング, ショート, ウルフ, レイヤー）、レングス、色（アッシュ, ベージュ, グレージュ, ピンク, ラベンダー, シルバー, ブラウン）、技術（カット, カラー, パーマ, トリートメント, 縮毛矯正, ハイライト, ブリーチ）などを**具体的に、かつ複数組み合わせる**ことを意識してください。
- **禁止事項:**
    - サロン名、スタイリスト名、クーポンIDなど、**固有の情報は絶対に含めないでください。**

【メニュー】(ちょうど{config.CHAR_LIMITS['menu']}文字に近づける)
- 具体的な施術内容をすべて含める（カット、カラー、トリートメントなど）
- 付加価値のある組み合わせを提案（○○込み、○○無料など）
- オプションやケアアイテムも含める
- 特別なテクニックや商材名を入れる
- トレンド感のある施術名を使用
- 価格やお得感を表現

【コメント】(ちょうど{config.CHAR_LIMITS['comment']}文字に近づける)
- 施術による具体的な効果や変化を詳しく説明
- お客様の悩みに対する解決策を提示
- 施術後のイメージを魅力的に描写
- 長期的なメリットを含める
- 季節やトレンドに合わせたアピールポイント
- 専門的なテクニックや商材の説明
- お客様の具体的なメリットを説明
- 施術プロセスの特徴を説明
- 他サロンとの差別化ポイントを強調
- **必ず90-120文字の範囲で生成してください**

**良いコメント例（100-120文字を目安）:**
**レディース例:**
*   `透けるような透明感のミルクティーグレージュ。ブリーチよりも傷まず、ノンカラーよりも圧倒的に透明感がでるので、現状の髪色が暗めの方、いつもオレンジになってしまう方はこちらがおススメです♪` (92文字)
*   `大人気のハイトーンカラー＊綺麗なハイトーンを維持するには2ヶ月半でのリタッチがオススメです＊綺麗なブリーチのベースを作ることで色落ちも気になりにくくなり、ストレスなくハイトーンを続けられます＊ぜひお任せください！` (106文字)
*   `気に入ったスタイルは【ブックマーク】をしていただくと便利です！顔形に合わせた小顔似合わせカットが大人気の20代30代から40代50代まで幅広い年齢層の方にご来店いただいています。ヘアスタイルでお悩みの方はお気軽にご相談ください♪` (114文字)
*   `【気に入ったスタイルはブックマークをしていただくと便利です】ミディアムが得意です☆20、30代の女性から幅広い年齢層の方にご来店いただいております。ヘアスタイルでお悩みの方はお気軽にご相談ください♪` (99文字)
*   `ショート、ボブ、パーマが得意です！朝が楽になる素敵なスタイルをご提案させて頂きます。ショートスタイルやパーマなどでお悩みの方はお気軽にご相談ください！気に入ったスタイルは【ブックマーク】してご提示ください♪` (103文字)
*   `ショート・ボブ・ミディアムが得意。２０、３０代のOLさんから４０、５０代の主婦の方まで幅広くご来店いただいています。白髪染めやパーマなどでお悩みの方はお気軽にご相談ください。気に入ったスタイルは【ブックマーク】すると便利です♪` (113文字)

**メンズ例:**
*   `【気に入ったスタイルはブックマークをしておくと便利です】ワックスだけで仕上がる、センターパートショートスタイル！あなただけの似合わせスタイルをご提案いたします！このスタイルをご希望の場合は【〇〇】をご指名下さい！` (106文字)
*   `頭の形が綺麗に見えるよう常に意識をしています！パーマをかけることでより骨格補正効果、スタイリングも簡単！学生はもちろん、社会人の方にもオススメ！黒髪相性良し！誰もが悩む絶壁、ハチ張り一緒に解消しましょう！` (114文字)
*   `マッシュショートの爽やかスタイル！時間のない朝にも時短でできる朝ラクヘア！10代から20代、30代から40代、50代と幅広く人気の王道スタイルです！外国人風の奥行きと骨格補正で似合わせバツグン！` (97文字)
*   `ツイストスパイラルパーマで今一番かっこいい髪型です♪ツイスパならではの動きを質感でだしつつ、やり過ぎない動きに仕上げました。ナチュラルでも、ウェットでも、ドライでも質感の好みやその日の気分で雰囲気を変えてもかっこよくキマります☆` (114文字)
*   `軽めのオイルをつけて乾かし、ハードワックスとバームを混ぜて全体馴染ませるだけで完成！ラフに何となくセットするだけでも決まります。他にもメンズスタイルを載せていますので他のスタイルも是非見てみてください！` (105文字)
*   `【気に入ったスタイルはブックマークをしておくと便利です】お客様の要望に応じて、ブロックを入れることで、スッキリとした印象を演出しました。フェードカットで輪郭を引き立て、スタイリッシュな雰囲気を実現しました。外国人風に爽やかに仕上げます！` (118文字)

**重要**: 上記の例のように、**必ず100-120文字程度**の十分な情報量のあるコメントを生成してください。短すぎるコメント（80文字未満など）は避けてください。**120文字を超えるコメントは生成しないでください。**

【ハッシュタグ】(各{config.CHAR_LIMITS['hashtag']}文字以内、7個以上)
- トレンドのキーワードを含める
- 施術内容に関連するタグを網羅
- 検索されやすい一般的なタグ（ヘアスタイル、トレンド、美容室など）
- 特徴的なタグ（具体的な技法、商材名など）
- 季節やイベント関連のタグ
- 地域や客層に関連するタグ
- スタイルの特徴を表すタグ
- **`#` は含めず、文字列の配列（リスト）として生成してください。**

**良いハッシュタグ例（7-10個を目安）:**
*   `["髪質改善", "透明感カラー", "艶髪", "ストレートヘア", "トリートメント", "美髪", "サラサラ", "ダメージケア", "美容室", "ヘアスタイル"]` (10個)
*   `["ハイトーン", "ブリーチ", "透明感", "カラー", "美容院", "ヘアカラー", "トレンド", "おしゃれ", "スタイリング", "ヘアケア"]` (10個)
*   `["ショートヘア", "ボブ", "パーマ", "カット", "美容室", "ヘアスタイル", "おしゃれ", "トレンド", "スタイリング", "ヘアケア"]` (10個)
*   `["韓国風", "マッシュ", "ニュアンスパーマ", "無造作", "メンズヘア", "おしゃれ", "トレンド", "ヘアスタイル", "美容院", "カット"]` (10個)

**重要**: 上記の例のように、**必ず7-10個程度**の関連性の高いハッシュタグを生成してください。少なすぎるハッシュタグ（5個未満など）は避けてください。

制約条件：
- title: ちょうど{config.CHAR_LIMITS['title']}文字に近づける（27-30文字）
- menu: ちょうど{config.CHAR_LIMITS['menu']}文字に近づける（45-50文字）
- comment: **厳守** {config.CHAR_LIMITS['comment']}文字以内（90-120文字を推奨、120文字を超えてはいけない）
- hashtagの各ワード: {config.CHAR_LIMITS['hashtag']}文字以内、7個以上のタグを含める

**文字数制限の厳守が最重要です。特にコメントは90-120文字の範囲で生成し、120文字を絶対に超えないでください。**

固有名詞（商品名、ブランド名）は避け、汎用的な表現を使用してください。

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
            logger.info("Gemini APIリクエスト送信中（新SDK + thinking_budget=0）...")
            
            # 新しいSDKでthinking_budget=0を設定
            try:
                config_with_thinking = types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=0  # 高速化のため思考プロセスを無効化
                    )
                )
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config_with_thinking
                )
                response_text = response.text
                logger.info("新SDK使用（thinking_budget=0）")
            except Exception as e:
                logger.warning(f"新SDK使用失敗、旧SDKにフォールバック: {str(e)}")
                # 旧SDKにフォールバック
                generation_config = genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                )
                response = await self.model.generate_content_async(prompt, generation_config=generation_config)
                response_text = response.text
                logger.info("旧SDK使用")
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