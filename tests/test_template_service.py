"""template_service の単体テスト。

これまで API 経由の間接テストしか無く、_attach_metadata が
何を付けるかを直接検証するテストが存在しなかった。
"""

import pytest

from app.services.keyword_analysis import KeywordAnalysis, analyze_keyword
from app.services.template_service import MIXED_KEYWORD_NOTE, _attach_metadata

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


class TestAttachMetadata:
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
            assert template['keyword_type'] == 'normal'
            assert template['processing_mode'] == 'standard'
            assert template['original_keyword'] == 'ボブ'
            assert template['is_mixed_keyword'] is False
            # 特集でないときは特集用のキーを増やさない
            assert 'featured_keyword_name' not in template
            assert 'mixed_processing_note' not in template

    def test_featured_keyword(self):
        analysis = analyze_keyword('くびれヘア', 'ladies', _FeaturedRepo())
        templates = raw_templates()

        _attach_metadata(templates, analysis)

        for template in templates:
            assert template['is_featured'] is True
            assert template['featured_keyword_name'] == 'テスト用くびれヘア'
            assert template['featured_condition'] == FEATURED['condition']
            assert template['featured_gender'] == 'ladies'
            assert template['is_mixed_keyword'] is False

    def test_mixed_keyword_gets_note(self):
        analysis = analyze_keyword('くびれヘア ボブ', 'ladies', _FeaturedRepo())
        templates = raw_templates()

        _attach_metadata(templates, analysis)

        assert analysis.keyword_type == 'mixed'
        for template in templates:
            assert template['is_mixed_keyword'] is True
            assert template['mixed_processing_note'] == MIXED_KEYWORD_NOTE

    def test_all_templates_get_the_same_metadata(self):
        """メタデータはリクエスト単位の情報なので全件に同じ値が入る"""
        analysis = analyze_keyword('くびれヘア', 'ladies', _FeaturedRepo())
        templates = raw_templates(count=5)

        _attach_metadata(templates, analysis)

        keys = ('is_featured', 'keyword_type', 'processing_mode', 'original_keyword')
        first = {k: templates[0][k] for k in keys}
        assert all({k: t[k] for k in keys} == first for t in templates)

    def test_empty_list_is_noop(self):
        analysis = analyze_keyword('ボブ', 'ladies', _FeaturedRepo())
        templates = []

        _attach_metadata(templates, analysis)

        assert templates == []


class _FeaturedRepo:
    """くびれヘアだけを特集として扱う最小のリポジトリ"""

    def is_available(self):
        return True

    def get_keyword_info(self, keyword):
        return FEATURED if keyword.strip() == 'くびれヘア' else None


@pytest.mark.asyncio
class TestGenerateTemplatesForRequest:
    async def test_returns_empty_when_no_titles(self, fake_scraper):
        """スクレイピング結果が0件なら生成へ進まない"""
        from app.services.template_service import generate_templates_for_request

        with fake_scraper(titles=[]):
            templates, trending = await generate_templates_for_request(
                '存在しないキーワード', 'ladies', repository=_FeaturedRepo()
            )

        assert templates == []
        assert trending == []

    async def test_attaches_metadata_to_generated_templates(self, fake_pipeline):
        """生成結果にメタデータが付いて返る"""
        from app.services.template_service import generate_templates_for_request

        with fake_pipeline(templates=raw_templates()):
            templates, _ = await generate_templates_for_request(
                'くびれヘア', 'ladies', repository=_FeaturedRepo()
            )

        assert len(templates) == 2
        for template in templates:
            assert template['is_featured'] is True
            assert template['featured_keyword_name'] == 'テスト用くびれヘア'
