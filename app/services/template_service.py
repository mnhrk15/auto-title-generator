"""スクレイピングとテンプレート生成の協調。

キーワード解析（keyword_analysis）の結果を受けて、
スクレイパーとジェネレーターを順に呼び出し、結果にメタデータを付けて返す。
"""

import logging
from dataclasses import dataclass

from ..config import DEFAULT_MODEL
from ..errors import NoResultsError
from ..generator import TemplateGenerator
from ..scraping import HotPepperScraper
from .keyword_analysis import (
    MODE_FEATURED,
    KeywordAnalysis,
    analyze_keyword,
)

logger = logging.getLogger(__name__)

# ログに出力するスクレイピング結果の最大件数（全件出すとログが肥大するため）
MAX_LOGGED_TITLES = 10


@dataclass(frozen=True)
class GenerationOutcome:
    """1 リクエスト分の生成結果。

    is_featured / featured_info はリクエスト単位の情報なので、
    テンプレートの中ではなくここに持たせる。以前はテンプレート 20 件全部に
    同じ値を書き込み、ルートが templates[0] から読み戻していた。
    """

    templates: list[dict]
    is_featured: bool
    featured_info: dict | None


def _log_scraped_titles(titles: list[str]) -> None:
    logger.debug(f"スクレイピングで取得した全タイトルリスト: {titles}")
    logger.info(f'スクレイピング結果のタイトル例 (最大{MAX_LOGGED_TITLES}件):')
    for i, title in enumerate(titles[:MAX_LOGGED_TITLES]):
        logger.info(f'  {i + 1}: {title}')
    if len(titles) > MAX_LOGGED_TITLES:
        logger.info(f'  ... 他 {len(titles) - MAX_LOGGED_TITLES} 件')


def _attach_metadata(templates: list[dict], analysis: KeywordAnalysis) -> None:
    """テンプレート 1 件ごとに必要なメタデータを付ける。

    ここに置くのは「カードごとに表示が変わる」情報だけ。
    リクエスト単位の情報は GenerationOutcome が持つ。
    """
    featured_name = (analysis.featured_info or {}).get('name', '') if analysis.is_featured else ''

    for template in templates:
        template['is_featured'] = analysis.is_featured
        if featured_name:
            template['featured_keyword_name'] = featured_name


async def generate_templates_for_request(
    keyword: str,
    gender: str,
    repository,
    seasons: list[str] | None = None,
    model: str = DEFAULT_MODEL,
) -> GenerationOutcome:
    """スクレイピングとテンプレート生成を実行する。

    Args:
        keyword: 検索キーワード
        gender: 'ladies' または 'mens'
        repository: 特集キーワードのリポジトリ
        seasons: 正規化済みの季節・カラー選択
        model: 使用する Gemini モデル

    Raises:
        NoResultsError: キーワードに一致するヘアスタイルが 1 件も無い場合
    """
    logger.info(
        f'非同期処理開始: キーワード: "{keyword}", 性別: "{gender}", '
        f'季節・カラー選択: {seasons}, モデル: "{model}"'
    )

    analysis = analyze_keyword(keyword, gender, repository)
    logger.info(
        f'キーワード処理結果: タイプ={analysis.keyword_type}, '
        f'モード={analysis.processing_mode}, 特集対応={analysis.is_featured}'
    )
    if analysis.processing_mode == MODE_FEATURED:
        logger.info(f'特集情報: {analysis.featured_info["name"]}')

    async with HotPepperScraper() as scraper:
        logger.info(f'スクレイピング開始: キーワード: "{keyword}", 性別: "{gender}"')
        titles = await scraper.scrape_titles_async(keyword, gender)
        logger.info(f'スクレイピング結果: {len(titles)} 件のタイトルを取得')

    if not titles:
        # 「該当なし」はドメイン上の結果であってエラーではないが、
        # 空リストで返すとスクレイピング失敗と区別できないため例外にする。
        logger.warning(f'キーワード "{keyword}" に一致するヘアスタイルが見つかりませんでした')
        raise NoResultsError()

    _log_scraped_titles(titles)

    logger.info(
        f'テンプレート生成開始: タイトル数: {len(titles)}, 季節・カラー選択: {seasons}, '
        f'モデル: "{model}", 特集対応: {analysis.is_featured}, '
        f'処理モード: {analysis.processing_mode}'
    )
    generator = TemplateGenerator(model_name=model)
    templates, trending_keywords = await generator.generate_templates_async(
        titles,
        keyword,
        seasons,
        gender,
        featured_info=analysis.featured_info,
        generation_context=analysis.to_generation_context(),
    )

    logger.info(f'テンプレート生成成功 - {len(templates)}件のテンプレートを生成')
    if trending_keywords:
        logger.info(
            f'トレンドキーワード: '
            f'{[kw.get("keyword", "") for kw in trending_keywords if isinstance(kw, dict)]}'
        )

    _attach_metadata(templates, analysis)

    return GenerationOutcome(
        templates=templates,
        is_featured=analysis.is_featured,
        featured_info=analysis.featured_info,
    )
