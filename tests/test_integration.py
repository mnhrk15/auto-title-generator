import pytest
import os
from app.generator import TemplateGenerator
from app import config

class TestTemplateGeneratorIntegration:
    @pytest.fixture
    def generator(self):
        """実際のGemini APIを使用するTemplateGeneratorのインスタンスを作成"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set in environment")
        return TemplateGenerator()
    
    def test_generate_templates_with_real_api(self, generator):
        """実際のGemini APIを使用してテンプレートを生成"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"
        
        templates = generator.generate_templates(titles, keyword)
        
        # 基本的な検証
        assert isinstance(templates, list)
        assert len(templates) <= config.MAX_TEMPLATES
        
        # 各テンプレートの構造と制約を検証
        for template in templates:
            assert isinstance(template, dict)
            assert all(key in template for key in ["title", "menu", "comment", "hashtag"])
            
            # キーワードが含まれているか確認
            assert keyword in template["title"]
            
            # 文字数制限の検証
            assert len(template["title"]) <= config.CHAR_LIMITS["title"]
            assert len(template["menu"]) <= config.CHAR_LIMITS["menu"]
            assert len(template["comment"]) <= config.CHAR_LIMITS["comment"]
            
            # ハッシュタグの検証
            hashtags = template["hashtag"].split(",")
            assert all(len(tag.strip()) <= config.CHAR_LIMITS["hashtag"] for tag in hashtags)
            assert len(hashtags) >= 1
            
    def test_generate_templates_with_multiple_titles(self, generator):
        """複数のタイトルを入力として使用した場合のテスト"""
        titles = [
            "★髪質改善トリートメントで艶髪ストレート",
            "【髪質改善】憧れの艶髪ストレートヘア",
            "髪質改善×うる艶カラー"
        ]
        keyword = "髪質改善"
        
        templates = generator.generate_templates(titles, keyword)
        
        assert isinstance(templates, list)
        assert len(templates) <= config.MAX_TEMPLATES
        
        # 生成されたテンプレートが入力タイトルと完全に同じでないことを確認
        generated_titles = [template["title"] for template in templates]
        assert not any(title in titles for title in generated_titles)
        
    def test_generate_templates_with_different_keywords(self, generator):
        """異なるキーワードでの生成テスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keywords = ["髪質改善", "透明感カラー", "艶髪"]
        
        for keyword in keywords:
            templates = generator.generate_templates(titles, keyword)
            
            assert isinstance(templates, list)
            assert len(templates) <= config.MAX_TEMPLATES
            
            # 各テンプレートにキーワードが含まれているか確認
            for template in templates:
                assert keyword in template["title"]
                
    def test_api_error_handling(self, generator):
        """APIエラー時の処理をテスト"""
        # 無効な入力を使用してエラーを発生させる
        with pytest.raises(Exception):
            generator.generate_templates([], "")  # 空のタイトルリストと空のキーワード 