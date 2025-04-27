import google.generativeai as genai
from typing import List, Dict
import json
import logging
import asyncio
from . import config

# ロガーの設定
logger = logging.getLogger(__name__)

class TemplateGenerator:
    def __init__(self):
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        logger.info("TemplateGeneratorが初期化されました")
        
    def _create_prompt(self, titles: List[str], keyword: str) -> str:
        """プロンプトテンプレートの作成"""
        titles_json = json.dumps(titles, ensure_ascii=False, indent=2)
        prompt = f"""
あなたは日本の美容トレンドに詳しく、魅力的なコピーライティングが得意なマーケターです。
HotPepper Beautyの人気サロンで使用されている、効果的なタイトルやキャッチコピーの特徴を熟知しています。

以下のヘアスタイルタイトルリストは、HotPepper Beautyで「{keyword}」というキーワードで検索して得られた結果です：

{titles_json}

上記リストとキーワード「{keyword}」を参考に、最新トレンドを反映した、新しい魅力的なヘアスタイルタイトル案を{config.MAX_TEMPLATES}つ生成してください。
タイトルには必ずキーワード「{keyword}」を含めてください。

各要素の生成ガイドライン：

**良いタイトル例:**
以下は、魅力的で情報量が多いと考えられるタイトル例です。これらの例を参考に、構成、キーワードの選択、記号の使い方などを考慮してください。

*   `★大人可愛い透明感グレージュ◎20代30代40代美人ヘアくすみベージュ`
    *   ポイント: 開始記号★、印象(大人可愛い, 透明感)、色(グレージュ, くすみベージュ)、強調記号◎、ターゲット層(20代30代40代)、付加価値(美人ヘア)
*   `★大人可愛い丸みボブ◎20代30代イメチェン ピンクベージュ`
    *   ポイント: 開始記号★、印象(大人可愛い)、髪型(丸みボブ)、強調記号◎、ターゲット層(20代30代)、願望(イメチェン)、色(ピンクベージュ)
*   `★20代30代小顔韓国ヘア◎ブリーチなし アッシュブラック 大人美人`
    *   ポイント: 開始記号★、ターゲット層(20代30代)、願望(小顔)、スタイル(韓国ヘア)、強調記号◎、技術(ブリーチなし)、色(アッシュブラック)、印象(大人美人)
*   `★くびれボブ ミニウルフ◎透明感シルバーアッシュグレージュ ハイトーン`
    *   ポイント: 開始記号★、スタイル(くびれボブ, ミニウルフ)、強調記号◎、印象(透明感)、色(シルバーアッシュグレージュ)、技術(ハイトーン)

**【タイトル】(ちょうど{config.CHAR_LIMITS['title']}文字に近づける)**
- **構成:** 上記の良い例を参考に、「`[★] + [年代/ターゲット層(任意)] + [印象/願望(複数可)] + [髪型/スタイル(複数可)] + [◎強調キーワード(任意)] + [色/技術(複数可)]`」のような、**情報量が多く魅力的な順序**を意識してください。要素の順番は柔軟に変更可能ですが、冒頭は必ず「★」で始めてください。
- **記号:**
    - タイトルの冒頭には必ず「★」を使用してください。
    - 特に強調したいキーワードには「◎」を使用してください。（例: ★30代40代◎美髪改善トリートメント付きボブ）
    - 複数のスタイル名や色名を並列する場合は「×」を使用してください。（例: ★韓国風×くびれミディ）
- **キーワード:**
    - 上記の良い例や、以下の頻出キーワードリストを参考に、元のタイトルの内容や文脈に合わせて、**積極的に多くのキーワードを追加・調整**してください:
        `大人可愛い`, `小顔`, `美髪`, `艶髪`, `透明感`, `似合わせ`, `イメチェン`, `レイヤー`, `ウルフ`, `くびれ`, `韓国風`, `シースルーバング`, `ワイドバング`, `髪質改善`, `暗髪`, `暖色カラー`, `寒色カラー`, `インナーカラー`, `ハイライト`, `バレイヤージュ`, `縮毛矯正`, `デジタルパーマ` ...など
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

【ハッシュタグ】(各{config.CHAR_LIMITS['hashtag']}文字以内、7個以上)
- トレンドのキーワードを含める
- 施術内容に関連するタグを網羅
- 検索されやすい一般的なタグ（ヘアスタイル、トレンド、美容室など）
- 特徴的なタグ（具体的な技法、商材名など）
- 季節やイベント関連のタグ
- 地域や客層に関連するタグ
- スタイルの特徴を表すタグ
- [#]などの記号は不要で、キーワードのみをコンマ区切りで列挙する

制約条件：
- title: ちょうど{config.CHAR_LIMITS['title']}文字に近づける（27-30文字）
- menu: ちょうど{config.CHAR_LIMITS['menu']}文字に近づける（45-50文字）
- comment: ちょうど{config.CHAR_LIMITS['comment']}文字に近づける（100-120文字）
- hashtagの各ワード: {config.CHAR_LIMITS['hashtag']}文字以内、7個以上のタグを含める

固有名詞（商品名、ブランド名）は避け、汎用的な表現を使用してください。

結果は以下のJSON形式で出力してください:

[
  {{
    "title": "【タイトル】",
    "menu": "【メニュー】",
    "comment": "【コメント】",
    "hashtag": ["#ハッシュタグ1", "#ハッシュタグ2", ... ]
  }},
  ...
]
"""
        logger.debug(f"プロンプト作成: 入力タイトル数: {len(titles)}, キーワード: '{keyword}'")
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
            
            # タイトルにキーワードが含まれているかチェック
            if keyword.lower() not in template['title'].lower():
                logger.warning(f"タイトルにキーワード '{keyword}' が含まれていません: {template['title']}")
                return False
                
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
    
    async def generate_templates_async(self, titles: List[str], keyword: str) -> List[Dict[str, str]]:
        """テンプレートの非同期生成"""
        # 入力検証を追加
        if not titles:
            logger.error("タイトルリストが空です")
            raise ValueError("タイトルリストが空です")
        if not keyword:
            logger.error("キーワードが指定されていません")
            raise ValueError("キーワードが指定されていません")
            
        logger.info(f"非同期テンプレート生成開始: タイトル数: {len(titles)}, キーワード: '{keyword}'")
        prompt = self._create_prompt(titles, keyword)
        
        try:
            logger.info("Gemini APIリクエスト送信中...")
            # 非同期で処理するためにgenerate_contentをrun_in_executorで実行
            # Google APIが直接的な非同期をサポートしていないため、ThreadPoolExecutorを使用して実行
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))
            response_text = response.text
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
        
    def generate_templates(self, titles: List[str], keyword: str) -> List[Dict[str, str]]:
        """テンプレートの生成（同期版ラッパー）"""
        logger.info("同期版 generate_templates が呼び出されました - 内部で非同期処理を実行します")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.generate_templates_async(titles, keyword))
        finally:
            loop.close()