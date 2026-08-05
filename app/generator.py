from google import genai
from google.genai import types
from pydantic import ValidationError
from typing import List, Dict, Tuple, Optional
import json
import logging
from . import config
from .errors import AppError, ConfigurationError, GenerationError
from .prompts import build_generation_prompt
from .schemas import GenerationResult

# ロガーの設定
logger = logging.getLogger(__name__)

class TemplateGenerator:
    def __init__(self, model_name: Optional[str] = None, settings: Optional[config.Settings] = None):
        """テンプレート生成器を初期化する。

        Args:
            model_name: 使用する Gemini モデル。省略時は config.DEFAULT_MODEL。
            settings: 使用する設定。省略時はプロセス共有の設定を使う。
        """
        self.settings = settings or config.get_settings()

        if not self.settings.gemini_api_key:
            # サーバー側の設定不備であり、ユーザーの入力エラーではない（500 で返す）
            raise ConfigurationError(
                'Gemini API キーが設定されていません。管理者にお問い合わせください。'
            )

        # サポートされているモデルの検証
        model_name = model_name or config.DEFAULT_MODEL
        if model_name not in config.SUPPORTED_MODELS:
            logger.warning(f"Unsupported model: {model_name}, falling back to {config.DEFAULT_MODEL}")
            model_name = config.DEFAULT_MODEL

        self.model_name = model_name

        # Google GenAI SDKクライアント初期化
        self.client = genai.Client(api_key=self.settings.gemini_api_key)
        logger.info(f"TemplateGeneratorが初期化されました（モデル: {model_name}）")
        
    def _normalize_seasons(self, seasons: Optional[List[str]], gender: str) -> List[str]:
        """季節・カラー選択値を config の定義順に正規化する（未知値と重複を除去）

        メンズでは季節カラー／ブリーチなしカラーを一切扱わないため常に空リストを返す。
        """
        return config.normalize_seasons(seasons, gender)

    def _create_prompt(self, titles: List[str], keyword: str, seasons: List[str] = None, gender: str = 'ladies', featured_info: Dict = None, generation_context: Dict = None) -> str:
        """プロンプトテンプレートの作成（組み立ては app/prompts.py に委譲）"""
        return build_generation_prompt(titles, keyword, seasons, gender, featured_info, generation_context)

    def _extract_result(self, response) -> Tuple[List[Dict], List[Dict]]:
        """Gemini のレスポンスからテンプレートとトレンドキーワードを取り出す。

        response_schema による構造化出力を使っているため、
        通常は response.parsed をそのまま使える。

        Args:
            response: generate_content の戻り値

        Returns:
            (templates, trending_keywords) のタプル（いずれも辞書のリスト）

        Raises:
            GenerationError: 生成が途中で打ち切られた、または結果を解釈できない場合
        """
        self._check_finish_reason(response)

        result = response.parsed
        if not isinstance(result, GenerationResult):
            # 稀に parsed が None になることがあるので、生テキストから復元を試みる
            response_text = getattr(response, 'text', None)
            if not response_text:
                raise GenerationError('Gemini から空のレスポンスが返されました。再度お試しください。')
            try:
                data = json.loads(response_text)
                # トレンドキーワードは付随情報でしかない。欠落や null のために
                # テンプレート20件ごと失敗させる価値はないので空リストとして扱う。
                if isinstance(data, dict) and data.get('trending_keywords') is None:
                    data['trending_keywords'] = []
                result = GenerationResult.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"レスポンスの解釈に失敗: {str(e)}")
                logger.debug(f"エラーが発生したレスポンスの一部: {response_text[:200]}...")
                raise GenerationError() from e

        usage = getattr(response, 'usage_metadata', None)
        if usage is not None:
            logger.info(
                f"Gemini トークン使用量: prompt={getattr(usage, 'prompt_token_count', '不明')}, "
                f"candidates={getattr(usage, 'candidates_token_count', '不明')}, "
                f"total={getattr(usage, 'total_token_count', '不明')}"
            )

        trending_keywords = [kw.model_dump() for kw in result.trending_keywords]
        if trending_keywords:
            logger.info(
                f"トレンドキーワード分析結果: {json.dumps(trending_keywords, ensure_ascii=False)}"
            )

        return [t.model_dump() for t in result.templates], trending_keywords

    @staticmethod
    def _check_finish_reason(response) -> None:
        """生成が正常に完了したかを確認する。

        以前は finish_reason を見ていなかったため、出力トークン上限で打ち切られた場合も
        「JSON パースエラー」としか分からず原因を切り分けられなかった。
        """
        candidates = getattr(response, 'candidates', None)
        if not candidates:
            raise GenerationError('Gemini から候補が返されませんでした。再度お試しください。')

        finish_reason = getattr(candidates[0], 'finish_reason', None)
        if finish_reason is None or finish_reason == types.FinishReason.STOP:
            return

        messages = {
            types.FinishReason.MAX_TOKENS:
                '生成結果が長すぎて途中で打ち切られました。時間をおいて再度お試しください。',
            types.FinishReason.SAFETY:
                '安全性フィルタにより生成が中断されました。別のキーワードをお試しください。',
            types.FinishReason.RECITATION:
                '引用チェックにより生成が中断されました。別のキーワードをお試しください。',
        }
        logger.error(f"Gemini の生成が正常終了しませんでした: finish_reason={finish_reason}")
        raise GenerationError(messages.get(finish_reason))

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
                
            if len(template['hashtag']) < config.HASHTAG_MIN_COUNT:
                logger.warning(
                    f"ハッシュタグの数が少なすぎます: "
                    f"{len(template['hashtag'])} < {config.HASHTAG_MIN_COUNT}"
                )
                return False
                
            for tag in template['hashtag']:
                if len(tag) > config.CHAR_LIMITS['hashtag']:
                    logger.warning(f"ハッシュタグが長すぎます: {tag} ({len(tag)} > {config.CHAR_LIMITS['hashtag']})")
                    return False
            
            logger.debug(f"テンプレート検証成功: '{template['title']}'")
            return True
        except (KeyError, AttributeError, TypeError) as e:
            # TypeError: 値が文字列以外（数値・None など）で len() に失敗するケース
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
            # プロンプト全文は数KBあり毎リクエスト出すとログが肥大するため、規模だけ記録する
            logger.debug(f"プロンプト長: {len(prompt)} 文字")
            logger.info("Gemini APIリクエスト送信中（thinkingLevel=MINIMAL, 構造化出力）...")

            request_config = types.GenerateContentConfig(
                temperature=config.GEMINI_TEMPERATURE,
                max_output_tokens=config.GEMINI_MAX_OUTPUT_TOKENS,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.MINIMAL  # 高速化のため思考プロセスを最小化
                ),
                response_mime_type='application/json',
                response_schema=GenerationResult,
                http_options=types.HttpOptions(
                    timeout=config.GEMINI_REQUEST_TIMEOUT_MS,
                    retry_options=types.HttpRetryOptions(
                        attempts=config.GEMINI_RETRY_ATTEMPTS,
                        initial_delay=config.GEMINI_RETRY_INITIAL_DELAY,
                        max_delay=config.GEMINI_RETRY_MAX_DELAY,
                    ),
                ),
            )
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=request_config
            )
            logger.info("Gemini API応答受信")

            templates, trending_keywords = self._extract_result(response)
            logger.info(f"APIから {len(templates)} 件のテンプレートを受信")

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
                raise GenerationError(
                    '生成されたテンプレートがすべて条件を満たしませんでした。再度お試しください。'
                )

            if len(valid_templates) < config.MAX_TEMPLATES:
                # 自動リトライはしない（レイテンシが倍増し、生成品質の方針も変わるため）。
                # 件数が減った事実は運用で追えるようログに残す。
                logger.warning(
                    f"有効テンプレートが要求数に達しませんでした: "
                    f"要求={config.MAX_TEMPLATES}件 / 受信={len(templates)}件 / 有効={len(valid_templates)}件"
                )

            result_templates = valid_templates[:config.MAX_TEMPLATES]

            # 選択された季節・カラーキーワードを後処理で付加する
            self._apply_season_keywords(result_templates, selected_seasons)

            # 付加処理は上限を守るよう作られているが、検証→変更の順序になるため最後に確認する
            title_limit = config.CHAR_LIMITS['title']
            for template in result_templates:
                if len(template['title']) > title_limit:
                    logger.warning(
                        f"季節・カラー付加後にタイトルが上限を超えました: "
                        f"{len(template['title'])} > {title_limit} ('{template['title']}')"
                    )

            logger.info(f"テンプレート生成完了: {len(result_templates)} 件の有効なテンプレート")
            return result_templates, trending_keywords

        except (AppError, ValueError):
            # AppError はユーザー向けメッセージが確定済み、ValueError は入力検証エラー
            raise
        except Exception as e:
            logger.error(f"テンプレート生成エラー: {str(e)}", exc_info=True)
            raise GenerationError() from e