"""Gemini のレスポンス解釈。

genai.Client には依存しないので、擬似レスポンスを渡せば API キーなしでテストできる。
"""

import json
import logging

from google.genai import types
from pydantic import ValidationError

from .errors import GenerationError
from .schemas import GenerationResult

logger = logging.getLogger(__name__)


def check_finish_reason(response) -> None:
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
        types.FinishReason.MAX_TOKENS: (
            '生成結果が長すぎて途中で打ち切られました。時間をおいて再度お試しください。'
        ),
        types.FinishReason.SAFETY: (
            '安全性フィルタにより生成が中断されました。別のキーワードをお試しください。'
        ),
        types.FinishReason.RECITATION: (
            '引用チェックにより生成が中断されました。別のキーワードをお試しください。'
        ),
    }
    logger.error(f"Gemini の生成が正常終了しませんでした: finish_reason={finish_reason}")
    raise GenerationError(messages.get(finish_reason))


def extract_result(response) -> tuple[list[dict], list[dict]]:
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
    check_finish_reason(response)

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
