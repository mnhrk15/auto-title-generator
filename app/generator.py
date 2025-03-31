import google.generativeai as genai
from typing import List, Dict
import json
import logging
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

【タイトル】(ちょうど{config.CHAR_LIMITS['title']}文字に近づける)
- 注目を集める記号（★、◎など）で始める
- 年代やターゲット層を具体的に示す（20代30代、大人可愛いなど）
- 特別感や限定感を演出（期間限定、今だけ、特別価格など）
- 具体的な特徴や効果を盛り込む（小顔、透明感、艶感など）
- 組み合わせテクニックを表現（×、+、◎など）
- 季節感や流行を意識する
- 検索されやすいキーワードを含める

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

制約条件：
- title: ちょうど{config.CHAR_LIMITS['title']}文字に近づける（27-30文字）
- menu: ちょうど{config.CHAR_LIMITS['menu']}文字に近づける（45-50文字）
- comment: ちょうど{config.CHAR_LIMITS['comment']}文字に近づける（100-120文字）
- hashtagの各ワード: {config.CHAR_LIMITS['hashtag']}文字以内、7個以上のタグを含める

固有名詞（商品名、ブランド名）は避け、汎用的な表現を使用してください。

以下の形式でJSON配列として結果を返してください。必ず各要素の文字数制限を守ってください：

[
  {{
    "title": "★20代30代髪質改善×透明感◎艶髪ストレート",
    "menu": "カット+カラー+髪質改善トリートメント+炭酸スパ付き+ホームケア付き",
    "comment": "髪のうねりやパサつきでお悩みの方におすすめ。髪質改善トリートメントで、まとまりのある艶やかな髪へ。ダメージを受けにくい髪質に導きます。",
    "hashtag": "髪質改善,透明感カラー,艶髪,ストレートヘア,トリートメント,ダメージケア,サラツヤ"
  }},
  // 残りのテンプレートも同様の形式で
]

必ず上記のJSON形式を守り、文字数制限内で生成してください。

また、必ずキーワード「{keyword}」をすべてのタイトルに含めることを最優先してください。タイトルにキーワードが含まれていない場合、そのテンプレートは使用できません。
"""
        logger.debug(f"プロンプト作成: 入力タイトル数: {len(titles)}, キーワード: '{keyword}'")
        return prompt
        
    def _validate_template(self, template: Dict[str, str], keyword: str) -> bool:
        """テンプレートの文字数制限チェックとキーワード含有チェック"""
        try:
            # 文字数制限チェック
            if len(template['title']) > config.CHAR_LIMITS['title']:
                logger.warning(f"タイトルが文字数制限を超えています: {len(template['title'])} > {config.CHAR_LIMITS['title']}")
                return False
            if len(template['menu']) > config.CHAR_LIMITS['menu']:
                logger.warning(f"メニューが文字数制限を超えています: {len(template['menu'])} > {config.CHAR_LIMITS['menu']}")
                return False
            if len(template['comment']) > config.CHAR_LIMITS['comment']:
                logger.warning(f"コメントが文字数制限を超えています: {len(template['comment'])} > {config.CHAR_LIMITS['comment']}")
                return False
            
            # ハッシュタグの各要素の文字数チェック
            for tag in template['hashtag'].split(','):
                if len(tag.strip()) > config.CHAR_LIMITS['hashtag']:
                    logger.warning(f"ハッシュタグが文字数制限を超えています: '{tag.strip()}' ({len(tag.strip())} > {config.CHAR_LIMITS['hashtag']})")
                    return False
            
            # キーワードがタイトルに含まれているかチェック
            if keyword.lower() not in template['title'].lower():
                logger.warning(f"タイトルにキーワード '{keyword}' が含まれていません: '{template['title']}'")
                return False
                
            logger.debug(f"テンプレート検証成功: '{template['title']}'")
            return True
        except (KeyError, AttributeError) as e:
            logger.error(f"テンプレート検証エラー: {str(e)}")
            return False
        
    def generate_templates(self, titles: List[str], keyword: str) -> List[Dict[str, str]]:
        """テンプレートの生成"""
        # 入力検証を追加
        if not titles:
            logger.error("タイトルリストが空です")
            raise ValueError("タイトルリストが空です")
        if not keyword:
            logger.error("キーワードが指定されていません")
            raise ValueError("キーワードが指定されていません")
            
        logger.info(f"テンプレート生成開始: タイトル数: {len(titles)}, キーワード: '{keyword}'")
        prompt = self._create_prompt(titles, keyword)
        
        try:
            logger.info("Gemini APIリクエスト送信中...")
            response = self.model.generate_content(prompt)
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