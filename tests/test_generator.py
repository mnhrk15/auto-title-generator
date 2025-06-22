import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.generator import TemplateGenerator
import json

class TestTemplateGenerator:
    @pytest.fixture
    def generator(self):
        return TemplateGenerator()
        
    @pytest.fixture
    def mock_gemini_response(self):
        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {
                "title": "★髪質改善×透明感カラー◎艶髪ストレート",
                "menu": "カット+カラー+髪質改善トリートメント",
                "comment": "髪質改善トリートメントで、まとまりのある艶やかな髪へ。ダメージを受けた髪も、しっとりとした質感に仕上げます。",
                "hashtag": ["髪質改善", "透明感カラー", "艶髪", "ストレートヘア", "トリートメント"]
            }
        ])
        return mock_response
        
    def test_create_prompt(self, generator):
        """プロンプトが正しく生成されるかテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"
        
        prompt = generator._create_prompt(titles, keyword)
        
        # プロンプトに必要な要素が含まれているか確認
        assert keyword in prompt
        assert "[\n  \"" + titles[0] + "\"\n]" in prompt
        assert "文字以内" in prompt  # 文字数制限の指示が含まれているか
        assert "JSON形式" in prompt  # 出力形式の指示が含まれているか
        
    def test_validate_template_valid(self, generator):
        """有効なテンプレートのバリデーションテスト"""
        template = {
            "title": "★髪質改善×透明感カラー◎艶髪ストレート",  # 30文字以内
            "menu": "カット+カラー+髪質改善トリートメント",  # 50文字以内
            "comment": "髪質改善トリートメントで、まとまりのある艶やかな髪へ。",  # 120文字以内
            "hashtag": ["髪質改善", "透明感カラー", "艶髪", "ストレートヘア", "トリートメント", "美髪", "サラサラ"]
        }
        
        assert generator._validate_template(template, "髪質改善") is True
        
    def test_validate_template_invalid_title(self, generator):
        """タイトルが文字数制限を超えている場合のテスト"""
        template = {
            "title": "★" * 31,  # 31文字（制限超過）
            "menu": "カット+カラー",
            "comment": "コメント",
            "hashtag": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5", "タグ6", "タグ7"]
        }
        
        assert generator._validate_template(template, "test") is False
        
    def test_validate_template_invalid_hashtag_length(self, generator):
        """ハッシュタグが文字数制限を超えている場合のテスト"""
        template = {
            "title": "★髪質改善",
            "menu": "カット+カラー",
            "comment": "コメント",
            "hashtag": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5", "タグ6", "これは20文字を超える非常に長いハッシュタグです"]
        }
        
        assert generator._validate_template(template, "髪質改善") is False

    def test_validate_template_invalid_hashtag_count(self, generator):
        """ハッシュタグの数が不足している場合のテスト"""
        template = {
            "title": "★髪質改善",
            "menu": "カット+カラー",
            "comment": "コメント",
            "hashtag": ["タグ1", "タグ2"] # 7個未満
        }

        assert generator._validate_template(template, "髪質改善") is False
        
    @pytest.mark.asyncio
    async def test_generate_templates_success(self, generator, mock_gemini_response):
        """テンプレート生成の正常系テスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"
        
        # 非同期メソッドをモックするためにAsyncMockを使用
        with patch('google.generativeai.GenerativeModel.generate_content_async', new_callable=AsyncMock, return_value=mock_gemini_response) as mock_generate_content:
            templates = await generator.generate_templates_async(titles, keyword)
            
            assert len(templates) == 1
            template = templates[0]
            assert "髪質改善" in template["title"]
            assert len(template["title"]) <= 30
            assert len(template["menu"]) <= 50
            assert len(template["comment"]) <= 120
            assert isinstance(template["hashtag"], list)
            assert all(len(tag) <= 20 for tag in template["hashtag"])
            
    @pytest.mark.asyncio
    async def test_generate_templates_invalid_response(self, generator):
        """APIからの無効なレスポンスの処理テスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"
        
        # 無効なJSONを返すモックレスポンス
        mock_response = MagicMock()
        mock_response.text = "invalid json"
        
        with patch('google.generativeai.GenerativeModel.generate_content_async', new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(ValueError, match="Invalid JSON response from Gemini API"):
                await generator.generate_templates_async(titles, keyword)
                
    @pytest.mark.asyncio
    async def test_generate_templates_no_valid_templates(self, generator):
        """有効なテンプレートが生成されない場合のテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"
        
        # 文字数制限を超えるテンプレートを返すモックレスポンス
        mock_response = MagicMock()
        mock_response.text = json.dumps([{
            "title": "★" * 31,  # 制限超過
            "menu": "メニュー",
            "comment": "コメント",
            "hashtag": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5", "タグ6", "タグ7"]
        }])
        
        with patch('google.generativeai.GenerativeModel.generate_content_async', new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(ValueError, match="No valid templates generated"):
                await generator.generate_templates_async(titles, keyword)
                
    @pytest.mark.asyncio
    async def test_generate_templates_api_error(self, generator):
        """API呼び出しエラーのテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"
        
        with patch('google.generativeai.GenerativeModel.generate_content_async', new_callable=AsyncMock, side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="Template generation failed: API Error"):
                await generator.generate_templates_async(titles, keyword) 