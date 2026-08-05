"""特集キーワード一覧の組み立て。

性別による絞り込みと、公開フィールドへの投影を行う。
Flask に依存しないので、アプリケーションコンテキストなしでテストできる。
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..errors import AppError, FeaturedKeywordsError

if TYPE_CHECKING:
    from ..featured_keywords import FeaturedKeywordRepository

logger = logging.getLogger(__name__)

# API が外に出すフィールド。リポジトリが余分なキーを持っていても漏らさない。
PUBLIC_FIELDS = ('name', 'keyword', 'gender', 'condition')

NO_KEYWORDS_MESSAGE = '現在、特集キーワードが設定されていません。'


@dataclass(frozen=True)
class FeaturedKeywordsView:
    """一覧の表示に必要な情報。

    message が入っているときは「リクエストは成功したが機能が降格している」状態で、
    フロントエンドはこれを見て通常のテンプレート生成を継続できる。
    """

    keywords: list[dict]
    message: str | None = None


def _degraded_message(last_error: Exception | None) -> str:
    """降格時にユーザーへ出す文言を決める。

    例外インスタンスの message にはファイルパスなど内部情報が入りうるので、
    クラス属性の DEFAULT_MESSAGE を使う。
    """
    if isinstance(last_error, AppError):
        return type(last_error).DEFAULT_MESSAGE
    if last_error is not None:
        return FeaturedKeywordsError.DEFAULT_MESSAGE
    return NO_KEYWORDS_MESSAGE


def list_featured_keywords(
    repository: 'FeaturedKeywordRepository', gender: str
) -> FeaturedKeywordsView:
    """指定された性別の特集キーワード一覧を返す。

    Args:
        repository: 特集キーワードのリポジトリ
        gender: 'ladies' または 'mens'

    Raises:
        FeaturedKeywordsError: リポジトリからの取得自体に失敗した場合
    """
    # 保護するのはリポジトリ境界だけにする。ここを広く囲うと、
    # 下の投影処理のバグまで「機能の降格」として握りつぶされる。
    try:
        available = repository.is_available()
        all_keywords = repository.get_all_keywords() if available else []
    except Exception as e:
        raise FeaturedKeywordsError() from e

    if not available:
        last_error = repository.get_last_error()
        if last_error is not None:
            logger.warning(f'特集キーワード機能が利用できません: {last_error}')
        else:
            logger.warning('特集キーワードが設定されていません')
        logger.debug(f'特集キーワード機能の状態: {repository.get_health_status()}')
        return FeaturedKeywordsView(keywords=[], message=_degraded_message(last_error))

    filtered = [k for k in all_keywords if k.get('gender') == gender]

    # 欠けているフィールドがある項目は表示できないので落とす。
    # リポジトリはインターフェースなので、実装によっては不完全な項目が来うる。
    keywords = []
    for keyword in filtered:
        projected = {field: str(keyword.get(field, '')).strip() for field in PUBLIC_FIELDS}
        if all(projected.values()):
            keywords.append(projected)
        else:
            logger.warning(f'不完全な特集キーワードデータをスキップ: {keyword}')

    logger.info(f'特集キーワード: 全 {len(all_keywords)} 件中 {len(keywords)} 件 (対象: {gender})')
    return FeaturedKeywordsView(keywords=keywords)
