"""Gemini によるテンプレート生成。

このモジュールは Gemini クライアントの初期化とリクエストの送信だけを担う。
- プロンプトの組み立て … prompts.py
- レスポンスの解釈 ……… gemini_response.py
- テンプレートの検証 …… template_validation.py
- 季節・カラーの付加 …… seasons.py
"""

import logging

from google import genai
from google.genai import types

from . import config
from .errors import AppError, ConfigurationError, GenerationError, ValidationError
from .gemini_response import extract_result
from .prompts import build_generation_prompt
from .schemas import GenerationResult
from .seasons import apply_season_keywords
from .template_validation import validate_template

logger = logging.getLogger(__name__)


class TemplateGenerator:
    def __init__(self, model_name: str | None = None, settings: config.Settings | None = None):
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
            logger.warning(
                f"Unsupported model: {model_name}, falling back to {config.DEFAULT_MODEL}"
            )
            model_name = config.DEFAULT_MODEL

        self.model_name = model_name

        # Google GenAI SDKクライアント初期化
        self.client = genai.Client(api_key=self.settings.gemini_api_key)
        logger.info(f"TemplateGeneratorが初期化されました（モデル: {model_name}）")

    def _build_request_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
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

    async def generate_templates_async(
        self,
        titles: list[str],
        keyword: str,
        seasons: list[str] | None = None,
        gender: str = 'ladies',
        featured_info: dict | None = None,
        generation_context: dict | None = None,
    ) -> tuple[list[dict[str, str]], list[dict]]:
        """テンプレートの非同期生成

        Args:
            titles: スクレイピングで取得した既存タイトル
            keyword: 検索キーワード
            seasons: **正規化済みの** 季節・カラー選択（main.parse_generate_request が正規化する）
            gender: 'ladies' または 'mens'
            featured_info: 特集キーワード情報
            generation_context: キーワード解析の結果

        Returns:
            (valid_templates, trending_keywords) のタプル
        """
        if not titles:
            logger.error("タイトルリストが空です")
            raise ValidationError("タイトルリストが空です")
        if not keyword:
            logger.error("キーワードが指定されていません")
            raise ValidationError("キーワードが指定されていません")

        selected_seasons = seasons or []
        context = generation_context or {}

        logger.info(
            f"非同期テンプレート生成開始: タイトル数: {len(titles)}, キーワード: '{keyword}', "
            f"季節・カラー選択: {selected_seasons}, 性別: '{gender}', "
            f"特集対応: {featured_info is not None}, "
            f"キーワードタイプ: {context.get('keyword_type', 'normal')}, "
            f"処理モード: {context.get('processing_mode', 'standard')}"
        )
        prompt = build_generation_prompt(
            titles, keyword, selected_seasons, gender, featured_info, generation_context
        )

        try:
            # プロンプト全文は数KBあり毎リクエスト出すとログが肥大するため、規模だけ記録する
            logger.debug(f"プロンプト長: {len(prompt)} 文字")
            logger.info("Gemini APIリクエスト送信中（thinkingLevel=MINIMAL, 構造化出力）...")

            response = await self.client.aio.models.generate_content(
                model=self.model_name, contents=prompt, config=self._build_request_config()
            )
            logger.info("Gemini API応答受信")

            templates, trending_keywords = extract_result(response)
            logger.info(f"APIから {len(templates)} 件のテンプレートを受信")

            valid_templates = []
            for i, template in enumerate(templates):
                logger.debug(f"テンプレート {i + 1} の検証: {template.get('title', '不明')}")
                if validate_template(template, keyword):
                    valid_templates.append(template)
                else:
                    logger.warning(f"テンプレート {i + 1} は検証に失敗しました")

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
                    f"要求={config.MAX_TEMPLATES}件 / 受信={len(templates)}件 / "
                    f"有効={len(valid_templates)}件"
                )

            result_templates = valid_templates[: config.MAX_TEMPLATES]

            # 季節・カラーはプロンプトに入れず、ここで後処理として付加する。
            # apply_season_keywords は上限文字数を超えない範囲でしか付加しないので、
            # 付加後の再チェックは不要（不変条件は seasons.py 側が持つ）。
            apply_season_keywords(result_templates, selected_seasons)

            logger.info(f"テンプレート生成完了: {len(result_templates)} 件の有効なテンプレート")
            return result_templates, trending_keywords

        except AppError:
            # ユーザー向けメッセージが確定済みなのでそのまま通す
            raise
        except Exception as e:
            logger.error(f"テンプレート生成エラー: {str(e)}", exc_info=True)
            raise GenerationError() from e
