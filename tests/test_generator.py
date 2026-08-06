"""TemplateGenerator のテスト。

Gemini クライアントを差し替える必要があるので、ここだけ API キーを要する。
純粋なロジックのテストは test_seasons / test_template_validation /
test_gemini_response にある。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from google.genai import types

from app.errors import GenerationError
from app.generator import TemplateGenerator
from app.schemas import GeneratedTemplate, GenerationResult


class TestGenerateTemplatesAsync:
    """generate_templates_async のエラー分類のテスト"""

    @pytest.fixture
    def generator(self):
        return TemplateGenerator()

    @pytest.mark.asyncio
    async def test_generation_with_no_valid_templates_raises_generation_error(self, generator):
        """有効なテンプレートが1件も残らない場合は GenerationError

        AppError のサブクラスなので、ルート層で 502 GENERATION_ERROR として
        返る（想定外の例外による 500 と区別できる）。
        """
        parsed = GenerationResult(trending_keywords=[], templates=[])
        response = SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)],
            parsed=parsed,
            text=None,
            usage_metadata=None,
        )

        with patch.object(
            generator.client.aio.models, 'generate_content', new=AsyncMock(return_value=response)
        ):
            with pytest.raises(GenerationError):
                await generator.generate_templates_async(["タイトル"], "髪質改善")

    @pytest.mark.asyncio
    async def test_successful_generation(self, generator):
        """正常系。これまでモックによる正常系のテストが無かった"""
        parsed = GenerationResult(
            trending_keywords=[],
            templates=[
                GeneratedTemplate(
                    title='★髪質改善×艶髪ストレート',
                    menu='カット+トリートメント',
                    comment='まとまりのある艶やかな髪へ。',
                    hashtag=[
                        '髪質改善',
                        '艶髪',
                        'ストレート',
                        '美髪',
                        'サラサラ',
                        'トリートメント',
                        'カット',
                    ],
                )
            ],
        )
        response = SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)],
            parsed=parsed,
            text=None,
            usage_metadata=None,
        )

        with patch.object(
            generator.client.aio.models, 'generate_content', new=AsyncMock(return_value=response)
        ):
            templates, trending, unapplied = await generator.generate_templates_async(
                ['既存タイトル'], '髪質改善'
            )

        assert len(templates) == 1
        assert templates[0]['title'] == '★髪質改善×艶髪ストレート'
        assert trending == []
        assert unapplied == []

    @pytest.mark.asyncio
    async def test_seasons_are_appended_after_generation(self, generator):
        """季節・カラーはプロンプトではなく後処理で付加される"""
        parsed = GenerationResult(
            trending_keywords=[],
            templates=[
                GeneratedTemplate(
                    title='ボブ',
                    menu='カット',
                    comment='コメント',
                    hashtag=['ボブ', 'カット', '髪型', 'ヘア', 'サロン', 'スタイル', 'トレンド'],
                )
            ],
        )
        response = SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)],
            parsed=parsed,
            text=None,
            usage_metadata=None,
        )

        with patch.object(
            generator.client.aio.models, 'generate_content', new=AsyncMock(return_value=response)
        ) as mock_generate:
            templates, _, unapplied = await generator.generate_templates_async(
                ['既存タイトル'], 'ボブ', seasons=['spring']
            )

        assert '春カラー' in templates[0]['title']
        assert unapplied == []
        # プロンプトには季節・カラーを入れない
        prompt = mock_generate.call_args.kwargs['contents']
        assert '春カラー' not in prompt

    @pytest.mark.asyncio
    async def test_unapplied_seasons_are_returned(self, generator):
        """長いタイトルばかりで付加できなかったキーワードが unapplied として返る"""
        parsed = GenerationResult(
            trending_keywords=[],
            templates=[
                GeneratedTemplate(
                    title='あ' * 26,  # SEASON_APPEND_THRESHOLD 以上なので付加対象外
                    menu='カット',
                    comment='コメント',
                    hashtag=['ボブ', 'カット', '髪型', 'ヘア', 'サロン', 'スタイル', 'トレンド'],
                )
            ],
        )
        response = SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)],
            parsed=parsed,
            text=None,
            usage_metadata=None,
        )

        with patch.object(
            generator.client.aio.models, 'generate_content', new=AsyncMock(return_value=response)
        ):
            templates, _, unapplied = await generator.generate_templates_async(
                ['既存タイトル'], 'ボブ', seasons=['spring']
            )

        assert templates[0]['title'] == 'あ' * 26
        assert unapplied == ['spring']

    @pytest.mark.asyncio
    async def test_empty_titles_is_validation_error(self, generator):
        """入力検証は ValidationError（以前は生の ValueError だった）"""
        from app.errors import ValidationError

        with pytest.raises(ValidationError):
            await generator.generate_templates_async([], '髪質改善')

        with pytest.raises(ValidationError):
            await generator.generate_templates_async(['タイトル'], '')
