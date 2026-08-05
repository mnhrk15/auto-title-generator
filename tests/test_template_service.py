"""template_service の単体テスト。

これまで API 経由の間接テストしか無く、_attach_metadata が
何を付けるかを直接検証するテストが存在しなかった。
"""

import pytest

from app.errors import NoResultsError
from app.services.keyword_analysis import KeywordAnalysis, analyze_keyword
from app.services.template_service import _attach_metadata, generate_templates_for_request

FEATURED = {
    'name': 'テスト用くびれヘア',
    'keyword': 'くびれヘア',
    'gender': 'ladies',
    'condition': 'スタイル名に『くびれヘア』を含めること。',
}


def raw_templates(count=2):
    """生成器が返す素のテンプレート（メタデータなし）"""
    return [
        {
            'title': f'サンプルタイトル{i}',
            'menu': 'カット',
            'comment': 'コメント',
            'hashtag': ['#タグ'],
        }
        for i in range(count)
    ]


class _FeaturedRepo:
    """くびれヘアだけを特集として扱う最小のリポジトリ"""

    def is_available(self):
        return True

    def get_keyword_info(self, keyword):
        return FEATURED if keyword.strip() == 'くびれヘア' else None


class TestAttachMetadata:
    """テンプレート 1 件ごとに付くメタデータ。

    リクエスト単位の情報（keyword_type / processing_mode など）は
    GenerationOutcome が持つので、ここには入らない。
    """

    def test_normal_keyword(self):
        analysis = KeywordAnalysis(
            original_keyword='ボブ',
            normalized_keyword='ボブ',
            keyword_type='normal',
            processing_mode='standard',
            is_featured=False,
            featured_info=None,
        )
        templates = raw_templates()

        _attach_metadata(templates, analysis)

        for template in templates:
            assert template['is_featured'] is False
            # 特集でないときは特集用のキーを増やさない
            assert 'featured_keyword_name' not in template

    def test_featured_keyword(self):
        analysis = analyze_keyword('くびれヘア', 'ladies', _FeaturedRepo())
        templates = raw_templates()

        _attach_metadata(templates, analysis)

        for template in templates:
            assert template['is_featured'] is True
            assert template['featured_keyword_name'] == 'テスト用くびれヘア'

    def test_mixed_keyword_is_treated_as_featured(self):
        analysis = analyze_keyword('くびれヘア ボブ', 'ladies', _FeaturedRepo())
        templates = raw_templates()

        _attach_metadata(templates, analysis)

        assert analysis.keyword_type == 'mixed'
        for template in templates:
            assert template['is_featured'] is True
            assert template['featured_keyword_name'] == 'テスト用くびれヘア'

    def test_all_templates_get_the_same_metadata(self):
        analysis = analyze_keyword('くびれヘア', 'ladies', _FeaturedRepo())
        templates = raw_templates(count=5)

        _attach_metadata(templates, analysis)

        keys = ('is_featured', 'featured_keyword_name')
        first = {k: templates[0][k] for k in keys}
        assert all({k: t[k] for k in keys} == first for t in templates)

    def test_empty_list_is_noop(self):
        analysis = analyze_keyword('ボブ', 'ladies', _FeaturedRepo())
        templates = []

        _attach_metadata(templates, analysis)

        assert templates == []


@pytest.mark.asyncio
class TestGenerateTemplatesForRequest:
    async def test_raises_when_no_titles(self, fake_scraper):
        """スクレイピング結果が0件なら NoResultsError

        空リストで返すとスクレイピング失敗と区別できないため例外にしている。
        """
        with fake_scraper(titles=[]), pytest.raises(NoResultsError):
            await generate_templates_for_request(
                '存在しないキーワード', 'ladies', repository=_FeaturedRepo()
            )

    async def test_returns_outcome_with_request_level_metadata(self, fake_pipeline):
        """リクエスト単位の情報は outcome に載る（templates[0] から読み戻さない）"""
        with fake_pipeline(templates=raw_templates()):
            outcome = await generate_templates_for_request(
                'くびれヘア', 'ladies', repository=_FeaturedRepo()
            )

        assert outcome.is_featured is True
        assert outcome.featured_info['name'] == 'テスト用くびれヘア'
        assert len(outcome.templates) == 2
        for template in outcome.templates:
            assert template['is_featured'] is True
            assert template['featured_keyword_name'] == 'テスト用くびれヘア'

    async def test_normal_keyword_outcome(self, fake_pipeline):
        with fake_pipeline(templates=raw_templates()):
            outcome = await generate_templates_for_request(
                'ボブ', 'ladies', repository=_FeaturedRepo()
            )

        assert outcome.is_featured is False
        assert outcome.featured_info is None
