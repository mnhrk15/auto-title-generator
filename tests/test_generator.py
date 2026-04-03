import pytest
from app.generator import TemplateGenerator

class TestTemplateGenerator:
    @pytest.fixture
    def generator(self):
        return TemplateGenerator()
        
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

    def test_create_prompt_includes_pv_boost_keywords(self, generator):
        """PV向上キーワードの指示がプロンプトに含まれるかテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"

        prompt = generator._create_prompt(titles, keyword)

        assert "PV向上キーワードの配置ルール" in prompt
        assert "ブリーチなしカラー" in prompt
        assert "春カラー" in prompt
        assert "夏カラー" in prompt
        assert "秋カラー" in prompt
        assert "冬カラー" in prompt
        # 配置ルールの番号が正しく計算されているか
        assert "タイトル1番目と2番目" in prompt
        assert "タイトル3番目と4番目" in prompt
        assert "タイトル9番目と10番目" in prompt

    def test_create_prompt_pv_keywords_with_season(self, generator):
        """シーズン指定時もPV向上キーワードが含まれるかテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"

        prompt = generator._create_prompt(titles, keyword, season="summer", gender="mens")

        assert "PV向上キーワードの配置ルール" in prompt
        assert "ブリーチなしカラー" in prompt
        assert "冬カラー" in prompt

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
        
