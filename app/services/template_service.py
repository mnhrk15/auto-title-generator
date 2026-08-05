"""スクレイピングとテンプレート生成の協調。

キーワード解析（keyword_analysis）の結果を受けて、
スクレイパーとジェネレーターを順に呼び出し、結果にメタデータを付けて返す。
"""

import logging
from typing import Dict, List, Optional, Tuple

from ..config import DEFAULT_MODEL
from ..generator import TemplateGenerator
from ..scraping import HotPepperScraper
from .keyword_analysis import (
    KEYWORD_TYPE_MIXED,
    KeywordAnalysis,
    MODE_FEATURED,
    analyze_keyword,
)

logger = logging.getLogger(__name__)

# ログに出力するスクレイピング結果の最大件数（全件出すとログが肥大するため）
MAX_LOGGED_TITLES = 10

MIXED_KEYWORD_NOTE = '特集キーワードと通常キーワードが混在しています'


def _log_scraped_titles(titles: List[str]) -> None:
    logger.debug(f"スクレイピングで取得した全タイトルリスト: {titles}")
    logger.info('スクレイピング結果のタイトル例 (最大%d件):' % MAX_LOGGED_TITLES)
    for i, title in enumerate(titles[:MAX_LOGGED_TITLES]):
        logger.info(f'  {i + 1}: {title}')
    if len(titles) > MAX_LOGGED_TITLES:
        logger.info(f'  ... 他 {len(titles) - MAX_LOGGED_TITLES} 件')


def _attach_metadata(templates: List[Dict], analysis: KeywordAnalysis) -> None:
    """生成されたテンプレートに、フロントエンドが参照するメタデータを付ける。"""
    is_mixed = analysis.keyword_type == KEYWORD_TYPE_MIXED
    featured_info = analysis.featured_info

    for template in templates:
        template['is_featured'] = analysis.is_featured
        template['keyword_type'] = analysis.keyword_type
        template['processing_mode'] = analysis.processing_mode
        template['original_keyword'] = analysis.original_keyword
        template['is_mixed_keyword'] = is_mixed

        if analysis.is_featured and featured_info:
            template['featured_keyword_name'] = featured_info.get('name', '')
            template['featured_condition'] = featured_info.get('condition', '')
            template['featured_gender'] = featured_info.get('gender', '')

        if is_mixed:
            template['mixed_processing_note'] = MIXED_KEYWORD_NOTE


async def generate_templates_for_request(
    keyword: str,
    gender: str,
    repository,
    seasons: Optional[List[str]] = None,
    model: str = DEFAULT_MODEL,
) -> Tuple[List[Dict], List[Dict]]:
    """スクレイピングとテンプレート生成を実行する。

    Args:
        keyword: 検索キーワード
        gender: 'ladies' または 'mens'
        repository: 特集キーワードのリポジトリ
        seasons: 正規化済みの季節・カラー選択
        model: 使用する Gemini モデル

    Returns:
        (templates, trending_keywords) のタプル。
        該当するヘアスタイルが無い場合は ([], [])。
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
        logger.warning(f'キーワード "{keyword}" に一致するヘアスタイルが見つかりませんでした')
        return [], []

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

    return templates, trending_keywords
