"""入力キーワードの解析。

「特集キーワードなのか、通常キーワードなのか、その混在なのか」を判定する。
I/O を持たない純粋なロジックなので、Flask コンテキストなしでテストできる。
"""

import logging
from dataclasses import dataclass, field

from .. import config

logger = logging.getLogger(__name__)

# キーワードの分類結果
KEYWORD_TYPE_FEATURED = 'featured'
KEYWORD_TYPE_NORMAL = 'normal'
KEYWORD_TYPE_MIXED = 'mixed'
KEYWORD_TYPE_ERROR = 'error'

# 生成時に使うプロンプトの経路
MODE_FEATURED = 'featured'
MODE_STANDARD = 'standard'
MODE_FALLBACK = 'fallback'

VALID_MODES = (MODE_FEATURED, MODE_STANDARD, MODE_FALLBACK)


@dataclass(frozen=True)
class KeywordAnalysis:
    """キーワード解析の結果。

    どの分岐を通っても全フィールドが必ず埋まるため、
    呼び出し側で変数の存在確認をする必要がない。
    """

    original_keyword: str
    normalized_keyword: str
    keyword_type: str
    processing_mode: str
    is_featured: bool
    featured_info: dict | None = None
    normal_keywords: list[str] = field(default_factory=list)

    def to_generation_context(self) -> dict:
        """TemplateGenerator に渡すコンテキスト情報。"""
        return {
            'keyword_type': self.keyword_type,
            'processing_mode': self.processing_mode,
            'original_keyword': self.original_keyword,
            'normalized_keyword': self.normalized_keyword,
        }


def split_keywords(keyword: str) -> list[str]:
    """複合キーワードを個々のキーワードに分割する。

    最初に見つかった区切り文字1種類だけで分割する（既存挙動を維持）。
    """
    for separator in config.KEYWORD_SEPARATORS:
        if separator in keyword:
            parts = [kw.strip() for kw in keyword.split(separator) if kw.strip()]
            logger.info(f'複数キーワードを検出しました: {parts}')
            return parts
    return [keyword]


def _standard(original: str, normalized: str, normal_keywords: list[str]) -> KeywordAnalysis:
    return KeywordAnalysis(
        original_keyword=original,
        normalized_keyword=normalized,
        keyword_type=KEYWORD_TYPE_NORMAL,
        processing_mode=MODE_STANDARD,
        is_featured=False,
        normal_keywords=normal_keywords,
    )


def analyze_keyword(keyword: str, gender: str, repository) -> KeywordAnalysis:
    """入力キーワードを解析して処理方針を決める。

    Args:
        keyword: ユーザーが入力したキーワード（複合キーワードもあり得る）
        gender: 'ladies' または 'mens'
        repository: 特集キーワードのリポジトリ（FeaturedKeywordsManager 互換）

    Returns:
        KeywordAnalysis: どの経路でも全フィールドが埋まった解析結果
    """
    original = keyword or ""
    normalized = original.strip()

    if not normalized:
        logger.warning('空のキーワードが入力されました - 通常処理を継続')
        return _standard(original, normalized, [])

    try:
        if not repository.is_available():
            logger.info(
                f'特集キーワード機能が利用できません - 通常キーワードとして処理: "{normalized}"'
            )
            return _standard(original, normalized, [normalized])

        featured_found = []
        normal_found = []

        for kw in split_keywords(normalized):
            kw = kw.strip()
            if not kw:
                continue

            kw_info = repository.get_keyword_info(kw)
            if kw_info:
                featured_found.append({'keyword': kw, 'info': kw_info})
                logger.info(
                    f'特集キーワードを検出: "{kw}" -> "{kw_info["name"]}" (性別: {kw_info["gender"]})'
                )
            else:
                normal_found.append(kw)
                logger.debug(f'通常キーワード: "{kw}"')

        if not featured_found and not normal_found:
            logger.warning(f'有効なキーワードが見つかりませんでした: "{normalized}"')
            return KeywordAnalysis(
                original_keyword=original,
                normalized_keyword=normalized,
                keyword_type=KEYWORD_TYPE_ERROR,
                processing_mode=MODE_FALLBACK,
                is_featured=False,
            )

        if not featured_found:
            logger.info(f'純粋通常キーワード処理: {normal_found}')
            return _standard(original, normalized, normal_found)

        # 複数の特集キーワードがある場合は最初のものを優先する
        primary = featured_found[0]
        featured_info = primary['info']
        is_mixed = bool(normal_found)

        if is_mixed:
            logger.info(f'混在キーワード処理: 特集キーワード "{primary["keyword"]}" を優先使用')
            logger.info(f'併用される通常キーワード: {normal_found}')
        else:
            logger.info(
                f'純粋特集キーワード処理: "{primary["keyword"]}" -> '
                f'"{featured_info["name"]}" (性別: {featured_info["gender"]})'
            )
            if len(featured_found) > 1:
                others = [f['keyword'] for f in featured_found[1:]]
                logger.info(f'その他の特集キーワード（参考情報として記録）: {others}')

        # 性別が一致しない場合も特集キーワードとして処理を継続する（仕様）
        if featured_info['gender'] != gender:
            logger.warning(
                f'特集キーワード "{primary["keyword"]}" の対象性別 ({featured_info["gender"]}) と '
                f'入力された性別 ({gender}) が一致しません - 特集キーワードの設定を優先します'
            )

        return KeywordAnalysis(
            original_keyword=original,
            normalized_keyword=normalized,
            keyword_type=KEYWORD_TYPE_MIXED if is_mixed else KEYWORD_TYPE_FEATURED,
            processing_mode=MODE_FEATURED,
            is_featured=True,
            featured_info=featured_info,
            normal_keywords=normal_found,
        )

    except Exception as e:
        logger.error(f'キーワード判定中にエラー: {str(e)} - 通常処理にフォールバック')
        return KeywordAnalysis(
            original_keyword=original,
            normalized_keyword=normalized,
            keyword_type=KEYWORD_TYPE_ERROR,
            processing_mode=MODE_FALLBACK,
            is_featured=False,
        )
