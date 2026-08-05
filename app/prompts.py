"""Gemini に渡す生成プロンプトの組み立て。

プロンプト文言とその組み立てロジックをここに集約する。純関数なので
API キーなしでテストでき、文言の変更が generator の変更と混ざらない。

性別ごとに違うのは語彙と例示だけなので、GENDER_VOCABULARY のデータとして持つ。
（以前は if/else の巨大な2ブロックがミラー構造で並んでいた）
"""

import json
import logging
from dataclasses import dataclass

from . import config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenderVocabulary:
    """性別ごとの語彙と例示。

    メンズ向けプロンプトにレディース向けのカラー語が混入しないよう、
    プロンプトに現れる性別依存の文字列はすべてここに集約する。
    """

    display_name: str
    keyword_examples: str
    title_keyword_hints: str
    specificity_hint: str
    title_examples: str
    comment_examples: str
    menu_examples: str
    symbol_examples: str
    hashtag_examples: str
    # 性別固有の追加注意点。該当がなければ空文字
    extra_note: str = ""


MENS_VOCABULARY = GenderVocabulary(
    display_name="メンズ",
    keyword_examples="（例: 20代30代 / 束感 / 韓国風 / 好印象）",
    title_keyword_hints=(
        "`小顔`, `束感`, `好印象`, `清潔感`, `爽やか`, `骨格補正`, `似合わせ`, `イメチェン`, "
        "`韓国風`, `外国人風`, `ツーブロック`, `センターパート`, `マッシュ`, `ウルフ`, `フェード`, "
        "`ニュアンスパーマ`, `ツイストパーマ`, `スパイラルパーマ` など"
    ),
    specificity_hint=(
        "髪型（ショート, マッシュ, ウルフ, センターパート, ツーブロック, フェード）、"
        "技術（カット, パーマ, ツイストパーマ, スパイラルパーマ, 刈り上げ）、"
        "印象（小顔効果, 骨格補正, 清潔感, 束感）を複数組み合わせてください。"
    ),
    title_examples="""- `小顔効果◎メンズパーマ波巻き×センターパート` (22文字) - ◎と×の組み合わせ
- `韓国風マッシュ/ニュアンスパーマ爽やか` (19文字) - /で区切り
- `韓国風マッシュニュアンスパーマ爽やか` (18文字) - 記号なし""",
    comment_examples="""- `頭の形が綺麗に見えるよう常に意識をしています！パーマをかけることでより骨格補正効果、スタイリングも簡単！学生はもちろん、社会人の方にもオススメ！黒髪相性良し！誰もが悩む絶壁、ハチ張り一緒に解消しましょう！` (102文字)
- `ツイストスパイラルパーマで今一番かっこいい髪型です♪ツイスパならではの動きを質感でだしつつ、やり過ぎない動きに仕上げました。ナチュラルでも、ウェットでも、ドライでも質感の好みやその日の気分で雰囲気を変えてもかっこよくキマります☆` (114文字)
- `マッシュショートの爽やかスタイル！時間のない朝にも時短でできる朝ラクヘア！10代から20代、30代から40代、50代と幅広く人気の王道スタイルです！外国人風の奥行きと骨格補正で似合わせバツグン！` (97文字)""",
    menu_examples="""- `カット+ツイストスパイラルパーマ+眉カット+スタイリング剤付き◎朝ラク時短で決まる束感ヘア` (45文字)
- `カット+ニュアンスパーマ+ヘッドスパ+眉カット込み◎骨格補正で小顔見えする韓国風マッシュ` (43文字)
- `カット+フェード+シェービング+スタイリング講習付き◎清潔感重視のビジネススタイル` (41文字)""",
    symbol_examples="""- 「◎」: キーワードの強調（例: 小顔効果◎センターパート）
- 「/」: キーワードの並列・区切り（例: マッシュ/韓国風/ニュアンスパーマ）
- 「◆」: 装飾・強調（例: 好印象メンズショート◆束感）
- 「×」: スタイルや技術の並列（例: ツーブロック×スパイラルパーマ）
- 記号なし: 自然な連結（例: 韓国風マッシュニュアンスパーマ爽やか）""",
    hashtag_examples='- `["韓国風", "マッシュ", "ニュアンスパーマ", "無造作", "メンズヘア", "おしゃれ", "トレンド", "ヘアスタイル", "美容院", "カット"]`',
    extra_note="""
- **メンズ特有キーワードの活用:**
    - ターゲット層: メンズ、20代30代、社会人、学生
    - スタイル: ツーブロック、センターパート、フェード、マッシュ、ショート
    - 技術: パーマ、ツイスパ、ニュアンスパーマ、波巻きパーマ
    - 効果: 小顔効果、骨格補正、清潔感、爽やか
    - 用途: ビジネス、カジュアル、オフィス
    - トレンド: 韓国風、外国人風、モダン
""",
)

LADIES_VOCABULARY = GenderVocabulary(
    display_name="レディース",
    keyword_examples="（例: 20代30代 / 透明感 / 韓国風 / 小顔）",
    title_keyword_hints=(
        "`大人可愛い`, `小顔`, `美髪`, `艶髪`, `透明感`, `似合わせ`, `イメチェン`, `レイヤー`, `ウルフ`, "
        "`くびれ`, `韓国風`, `シースルーバング`, `髪質改善`, `暗髪`, `インナーカラー`, `ハイライト`, "
        "`バレイヤージュ`, `縮毛矯正`, `デジタルパーマ` など"
    ),
    specificity_hint=(
        "髪型（ボブ, ミディアム, ロング, ショート, ウルフ, レイヤー）、"
        "色（アッシュ, ベージュ, グレージュ, ピンク, ラベンダー）、"
        "技術（カット, カラー, パーマ, トリートメント, ハイライト, ブリーチ）を複数組み合わせてください。"
    ),
    title_examples="""- `大人可愛い透明感グレージュ◎20代美人ヘア` (21文字) - ◎で強調
- `韓国風レイヤーカット/顔周り/くびれミディ` (20文字) - /で3要素並列
- `上品韓国ヘア◆グレージュ顔周りカット` (18文字) - ◆で装飾
- `くびれミディ×艶髪ラベンダーカラー30代` (20文字) - ×で並列
- `ミディアムレイヤー顔周りカラー韓国ヘア` (19文字) - 記号なしの自然連結
- `韓国風くびれレイヤー髪質改善透明感` (17文字) - 最小限の要素""",
    comment_examples="""- `透けるような透明感のミルクティーグレージュ。ブリーチよりも傷まず、ノンカラーよりも圧倒的に透明感がでるので、現状の髪色が暗めの方、いつもオレンジになってしまう方はこちらがおススメです♪` (92文字)
- `大人気のハイトーンカラー＊綺麗なハイトーンを維持するには2ヶ月半でのリタッチがオススメです＊綺麗なブリーチのベースを作ることで色落ちも気になりにくくなり、ストレスなくハイトーンを続けられます＊ぜひお任せください！` (106文字)
- `気に入ったスタイルは【ブックマーク】をしていただくと便利です！小顔似合わせカットが大人気。20代30代から40代50代まで幅広い年齢層の方にご来店いただいています。お悩みの方はお気軽にご相談ください♪` (100文字)""",
    menu_examples="""- `カット+透明感カラー+髪質改善トリートメント+炭酸スパ+前髪カット込み◎ダメージレスで艶髪に` (46文字)
- `カット+イルミナカラー+TOKIOトリートメント+ヘッドスパ+前髪カット込み◎うる艶カラーで美髪` (48文字)
- `カット+ダブルカラー+ケアブリーチ+カラーシャンプー付き+毛先トリートメント◎透明感ハイトーン` (47文字)""",
    symbol_examples="""- 「◎」: キーワードの強調（例: 小顔◎透明感カラー）
- 「/」: キーワードの並列・区切り（例: レイヤーカット/韓国/前髪カット）
- 「◆」: 装飾・強調（例: 上品韓国ヘア◆グレージュ）
- 「×」: スタイルや色の並列（例: 韓国風×くびれミディ）
- 記号なし: 自然な連結（例: ミディアムレイヤー顔周りカラー韓国ヘア）""",
    hashtag_examples='- `["髪質改善", "透明感カラー", "艶髪", "ストレートヘア", "トリートメント", "美髪", "サラサラ", "ダメージケア", "美容室", "ヘアスタイル"]`',
)

GENDER_VOCABULARY = {
    'ladies': LADIES_VOCABULARY,
    'mens': MENS_VOCABULARY,
}


def _target_range(target: tuple[int, int]) -> str:
    """(25, 28) -> '25〜28文字'"""
    return f"{target[0]}〜{target[1]}文字"


def short_title_slots_per_keyword(selected_count: int) -> int:
    """季節・カラー1つあたりに割り当てる短尺タイトル枠の数"""
    return max(
        1, min(config.SHORT_TITLE_SLOTS_PER_CHOICE, config.SHORT_TITLE_SLOTS_MAX // selected_count)
    )


def short_title_band_max(keyword: str) -> int:
    """このキーワードを付加してちょうど上限文字数に収まる、付加前のタイトル文字数"""
    # 区切り記号1文字ぶんを差し引く。付加対象にならない長さを指示しないよう閾値未満に抑える
    return min(config.CHAR_LIMITS['title'] - 1 - len(keyword), config.SEASON_APPEND_THRESHOLD - 1)


def build_featured_instruction(
    featured_info: dict | None,
    keyword: str,
    keyword_type: str,
    original_keyword: str,
) -> str:
    """特集キーワード向けの追加指示を組み立てる。

    特集情報が無い・不正な場合は空文字を返す（特集指示なしで生成を続行する）。
    """
    if not featured_info:
        return ""

    try:
        if not isinstance(featured_info, dict):
            logger.warning(
                f"特集情報が辞書形式ではありません: {type(featured_info)} - 特集機能をスキップ"
            )
            return ""

        if 'condition' not in featured_info or not featured_info['condition']:
            logger.warning("特集情報に条件が含まれていません - 特集機能をスキップ")
            return ""

        condition = str(featured_info['condition']).strip()
        # 上限はローダー側の検証と同じ値を使う（別々に持つと片方が到達不能になる）
        if len(condition) > config.FEATURED_CONDITION_MAX:
            logger.warning(
                f"特集条件文が長すぎます "
                f"({len(condition)} > {config.FEATURED_CONDITION_MAX}文字) - 切り詰めます"
            )
            condition = condition[: config.FEATURED_CONDITION_MAX] + "..."

        logger.debug(f"特集プロンプト強化を適用: キーワード '{keyword}', タイプ: {keyword_type}")

        if keyword_type == "mixed":
            return f"""

【重要】特集掲載条件の厳守（混在キーワード処理）
入力されたキーワード「{original_keyword}」には特集キーワード「{featured_info.get('name', keyword)}」が含まれています。
以下の特集掲載条件を絶対に満たすテンプレートを生成してください：

{condition}

混在キーワード処理のため、特集キーワードの条件を最優先としつつ、
他のキーワード要素も適切に組み込んでください。
特集掲載の対象外とならないよう、上記の条件を厳密に守ってください。

"""

        return f"""

【重要】特集掲載条件の厳守
このキーワード「{keyword}」は今月の特集キーワードです。
以下の条件を絶対に満たすテンプレートを生成してください：

{condition}

この条件を満たさないテンプレートは特集掲載の対象外となるため、
必ず上記の条件を最優先事項として考慮してください。
特に、タイトル生成時には上記の条件を厳密に守り、
指定されたキーワードや表現を必ず含めるようにしてください。

"""
    except Exception as e:
        logger.error(f"特集プロンプト生成中にエラー: {str(e)} - 特集機能をスキップ")
        return ""


def build_title_length_rule(selected_seasons: list[str]) -> tuple[str, str]:
    """タイトルの目標文字数ルールと補足を組み立てる。

    季節・カラーが選択されている場合、後処理で語句を付加する余白を確保するため
    一部のタイトルを短めに生成させる。付加語の長さごとに目標帯を分け、
    付加後にちょうど上限文字数へ届くようにする。

    Returns:
        (title_length_rule, short_title_note) のタプル
    """
    title_target = _target_range(config.TITLE_TARGET)

    if not selected_seasons:
        return f"- title: **{title_target}**を目標", ""

    slots_per_keyword = short_title_slots_per_keyword(len(selected_seasons))
    bands = {}
    for key in selected_seasons:
        band_max = short_title_band_max(config.SEASON_COLOR_CHOICES[key])
        bands[band_max] = bands.get(band_max, 0) + slots_per_keyword

    short_slots = sum(bands.values())
    band_rules = "、".join(
        f"**{slots}個は{band_max - config.SHORT_TITLE_BAND_WIDTH}〜{band_max}文字**"
        for band_max, slots in sorted(bands.items(), reverse=True)
    )
    title_length_rule = (
        f"- title: {config.MAX_TEMPLATES}個中{band_rules}、"
        f"残りの{config.MAX_TEMPLATES - short_slots}個は**{title_target}**を目標"
    )
    short_title_note = (
        "\n※ 短めの目標文字数を指定しているのは、後から語句を追記するための余白を残す目的です。"
        "追記する語句はこちらで決めるため、指定は不要です。"
        "追記後に上限文字数いっぱいまで活用できるよう、指定した文字数の**上限側に寄せて**作成してください。\n"
    )
    logger.debug(f"短尺タイトル枠 {bands} をプロンプトに追加（選択: {selected_seasons}）")

    return title_length_rule, short_title_note


def build_generation_prompt(
    titles: list[str],
    keyword: str,
    seasons: list[str] | None = None,
    gender: str = 'ladies',
    featured_info: dict | None = None,
    generation_context: dict | None = None,
) -> str:
    """テンプレート生成用のプロンプトを組み立てる。"""
    titles_json = json.dumps(titles, ensure_ascii=False, indent=2)

    vocabulary = GENDER_VOCABULARY.get(gender, LADIES_VOCABULARY)
    gender_name = vocabulary.display_name

    selected_seasons = seasons or []

    # 混在キーワード処理のための生成コンテキスト解析
    context = generation_context or {}
    keyword_type = context.get('keyword_type', 'normal')
    original_keyword = context.get('original_keyword', keyword)

    featured_instruction = build_featured_instruction(
        featured_info, keyword, keyword_type, original_keyword
    )
    title_length_rule, short_title_note = build_title_length_rule(selected_seasons)

    menu_target = _target_range(config.MENU_TARGET)
    comment_target = _target_range(config.COMMENT_TARGET)
    hashtag_min = config.HASHTAG_MIN_COUNT

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
- menu: **{menu_target}**を目標（上限{config.CHAR_LIMITS['menu']}文字。超えたら無効）
- comment: **{comment_target}**を目標（上限{config.CHAR_LIMITS['comment']}文字。超えたら無効）
- hashtag: 各ワード{config.CHAR_LIMITS['hashtag']}文字以内、{hashtag_min}個以上
{short_title_note}
### 重要: キーワード数の要求
タイトルには必ずキーワード「{keyword}」を含めてください。
**文字数制限内に収まる範囲で**、合計3〜5個程度のキーワードを盛り込んでください。
キーワード数を増やすより、文字数制限を守ることを優先してください。
{vocabulary.keyword_examples}

### 推奨: 表現の質
- **掘り下げキーワード:** 一般的な表現から一歩踏み込み、より具体的な表現を使用してください。
    - 例: 「ショートヘア」→「小顔ショート」「ハンサムショート」、「メンズパーマ」→「スパイラルパーマ」「ツイストパーマ」
- 固有名詞（サロン名、スタイリスト名、商品名、ブランド名）は避け、汎用的な表現を使用してください。

## 各要素の生成ガイドライン
{vocabulary.extra_note}
### 【タイトル】（上限{config.CHAR_LIMITS['title']}文字。目標文字数は「最重要: 文字数の厳守」に従ってください）

**構成パターン（参考）:**
`[印象/願望] + [スタイル/髪型] + [色/技術] + [ターゲット層(任意)]` のような要素を組み合わせるのが基本ですが、**あくまで参考**です。
要素の順番・有無・数は自由に調整してください。**文字数制限を守ることが最優先**なので、構成パターンに縛られて文字数超過するくらいなら、要素を減らして簡潔にまとめてください。

**記号ルール:**
参照データを見ると、上位スタイルでは「◎」「/」「◆」「×」「【】」などの記号が使われたり、記号なしのタイトルも多数あります。
Gemini側で**参照データのスタイルを参考に、自由に記号を選択**してください（記号なしでも構いません）。
以下は使用可能な記号の例です:
{vocabulary.symbol_examples}

**キーワード選定の参考（参照データのトレンド分析結果を優先してください）:**
{vocabulary.title_keyword_hints}

**ターゲット層:**
「20代30代」「30代40代」など年代を入れると検索に効果的ですが、**{config.MAX_TEMPLATES}個中{config.MAX_TEMPLATES // 2}個程度**に留めてください。残りには年代を入れず、スタイルや技術で差別化してください。

**具体性:**
{vocabulary.specificity_hint}

**良いタイトル例（記号の使い方のバリエーション）:**
{vocabulary.title_examples}

※記号なしや少ない記号でも十分に魅力的なタイトルになります。文字数オーバーするくらいなら要素を減らしてください。

### 【メニュー】（{menu_target}、上限{config.CHAR_LIMITS['menu']}文字）
- 具体的な施術内容をすべて含める（カット、カラー、トリートメントなど）
- 付加価値のある組み合わせを提案（○○込み、○○無料など）
- オプションやケアアイテム、特別なテクニックも含める
- トレンド感のある施術名を使用し、価格やお得感を表現

**良いメニュー例（{menu_target}）:**
{vocabulary.menu_examples}

### 【コメント】（{comment_target}、上限{config.CHAR_LIMITS['comment']}文字）
- 施術による具体的な効果や変化を詳しく説明
- お客様の悩みに対する解決策を提示
- 施術後のイメージを魅力的に描写
- トレンドに合わせたアピールポイントを含める

**良いコメント例（{comment_target}）:**
{vocabulary.comment_examples}

### 【ハッシュタグ】（各{config.CHAR_LIMITS['hashtag']}文字以内、{hashtag_min}個以上）
- トレンドのキーワード、施術内容、検索されやすい一般タグを網羅
- スタイルの特徴を表すタグも含める
- `#` は含めず、文字列の配列（リスト）として生成してください

**良いハッシュタグ例（{hashtag_min}〜10個）:**
{vocabulary.hashtag_examples}

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
    logger.debug(
        f"プロンプト作成: 入力タイトル数: {len(titles)}, キーワード: '{keyword}', "
        f"季節・カラー選択: {selected_seasons}, 性別: '{gender}'"
    )
    return prompt
