"""キーワード解析のユニットテスト。

analyze_keyword は I/O を持たない純粋なロジックなので、
Flask のアプリケーションコンテキストなしでテストできる。
"""

import pytest

from app.services.keyword_analysis import (
    KEYWORD_TYPE_ERROR,
    KEYWORD_TYPE_FEATURED,
    KEYWORD_TYPE_MIXED,
    KEYWORD_TYPE_NORMAL,
    MODE_FALLBACK,
    MODE_FEATURED,
    MODE_STANDARD,
    analyze_keyword,
    split_keywords,
)

LADIES_FEATURED = {
    'name': 'テスト用くびれヘア',
    'keyword': 'くびれヘア',
    'gender': 'ladies',
    'condition': 'スタイル名に「くびれヘア」を含めること',
}


class FakeRepository:
    """FeaturedKeywordsManager の最小限の代替"""

    def __init__(self, keywords=(), available=True):
        self._by_keyword = {k['keyword'].lower(): k for k in keywords}
        self._available = available

    def is_available(self):
        return self._available

    def get_keyword_info(self, keyword):
        return self._by_keyword.get(keyword.lower().strip())


class BrokenRepository:
    def is_available(self):
        raise RuntimeError('リポジトリが壊れている')


class TestSplitKeywords:
    @pytest.mark.parametrize('raw,expected', [
        ('くびれヘア', ['くびれヘア']),
        ('くびれヘア 髪質改善', ['くびれヘア', '髪質改善']),
        ('くびれヘア　髪質改善', ['くびれヘア', '髪質改善']),  # 全角スペース
        ('くびれヘア,髪質改善', ['くびれヘア', '髪質改善']),
        ('くびれヘア、髪質改善', ['くびれヘア', '髪質改善']),
        ('くびれヘア/髪質改善', ['くびれヘア', '髪質改善']),
        ('くびれヘア+髪質改善', ['くびれヘア', '髪質改善']),
        ('くびれヘア＋髪質改善', ['くびれヘア', '髪質改善']),
    ])
    def test_splits_on_each_separator(self, raw, expected):
        assert split_keywords(raw) == expected

    def test_ignores_empty_segments(self):
        assert split_keywords('くびれヘア  髪質改善') == ['くびれヘア', '髪質改善']


class TestAnalyzeKeyword:
    def test_pure_featured_keyword(self):
        repo = FakeRepository([LADIES_FEATURED])

        result = analyze_keyword('くびれヘア', 'ladies', repo)

        assert result.keyword_type == KEYWORD_TYPE_FEATURED
        assert result.processing_mode == MODE_FEATURED
        assert result.is_featured is True
        assert result.featured_info == LADIES_FEATURED
        assert result.normal_keywords == []

    def test_pure_normal_keyword(self):
        repo = FakeRepository([LADIES_FEATURED])

        result = analyze_keyword('髪質改善', 'ladies', repo)

        assert result.keyword_type == KEYWORD_TYPE_NORMAL
        assert result.processing_mode == MODE_STANDARD
        assert result.is_featured is False
        assert result.featured_info is None
        assert result.normal_keywords == ['髪質改善']

    def test_mixed_keywords_prioritize_featured(self):
        repo = FakeRepository([LADIES_FEATURED])

        result = analyze_keyword('くびれヘア 髪質改善', 'ladies', repo)

        assert result.keyword_type == KEYWORD_TYPE_MIXED
        assert result.processing_mode == MODE_FEATURED
        assert result.is_featured is True
        assert result.featured_info == LADIES_FEATURED
        assert result.normal_keywords == ['髪質改善']

    def test_gender_mismatch_still_uses_featured(self):
        """性別が一致しなくても特集キーワードとして処理を継続する（仕様）"""
        repo = FakeRepository([LADIES_FEATURED])

        result = analyze_keyword('くびれヘア', 'mens', repo)

        assert result.is_featured is True
        assert result.featured_info['gender'] == 'ladies'

    def test_repository_unavailable_falls_back_to_normal(self):
        repo = FakeRepository([LADIES_FEATURED], available=False)

        result = analyze_keyword('くびれヘア', 'ladies', repo)

        assert result.keyword_type == KEYWORD_TYPE_NORMAL
        assert result.processing_mode == MODE_STANDARD
        assert result.is_featured is False

    def test_empty_keyword(self):
        result = analyze_keyword('   ', 'ladies', FakeRepository([LADIES_FEATURED]))

        assert result.keyword_type == KEYWORD_TYPE_NORMAL
        assert result.processing_mode == MODE_STANDARD
        assert result.normalized_keyword == ''

    def test_repository_failure_falls_back(self):
        result = analyze_keyword('くびれヘア', 'ladies', BrokenRepository())

        assert result.keyword_type == KEYWORD_TYPE_ERROR
        assert result.processing_mode == MODE_FALLBACK
        assert result.is_featured is False

    def test_generation_context_is_always_complete(self):
        """どの分岐でもコンテキストの全キーが埋まる

        以前は main.py が locals() で変数の存在を確認しており、
        分岐によっては normalized_keyword が欠けうる構造だった。
        """
        repo = FakeRepository([LADIES_FEATURED])
        expected_keys = {
            'keyword_type', 'processing_mode', 'original_keyword', 'normalized_keyword',
        }

        for keyword, repository in [
            ('くびれヘア', repo),
            ('髪質改善', repo),
            ('くびれヘア 髪質改善', repo),
            ('', repo),
            ('くびれヘア', BrokenRepository()),
        ]:
            context = analyze_keyword(keyword, 'ladies', repository).to_generation_context()
            assert set(context.keys()) == expected_keys
            assert all(value is not None for value in context.values())
