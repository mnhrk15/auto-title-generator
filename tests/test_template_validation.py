"""テンプレート検証のテスト。

純粋なロジックなので TemplateGenerator（＝API キー）を必要としない。
"""

from app.template_validation import validate_template


class TestValidateTemplate:
    def test_validate_template_valid(self):
        """有効なテンプレートのバリデーションテスト"""
        template = {
            "title": "★髪質改善×透明感カラー◎艶髪ストレート",  # 30文字以内
            "menu": "カット+カラー+髪質改善トリートメント",  # 50文字以内
            "comment": "髪質改善トリートメントで、まとまりのある艶やかな髪へ。",  # 120文字以内
            "hashtag": [
                "髪質改善",
                "透明感カラー",
                "艶髪",
                "ストレートヘア",
                "トリートメント",
                "美髪",
                "サラサラ",
            ],
        }

        assert validate_template(template, "髪質改善") is True

    def test_validate_template_invalid_title(self):
        """タイトルが文字数制限を超えている場合のテスト"""
        template = {
            "title": "★" * 31,  # 31文字（制限超過）
            "menu": "カット+カラー",
            "comment": "コメント",
            "hashtag": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5", "タグ6", "タグ7"],
        }

        assert validate_template(template, "test") is False

    def test_validate_template_invalid_hashtag_length(self):
        """ハッシュタグが文字数制限を超えている場合のテスト"""
        template = {
            "title": "★髪質改善",
            "menu": "カット+カラー",
            "comment": "コメント",
            "hashtag": [
                "タグ1",
                "タグ2",
                "タグ3",
                "タグ4",
                "タグ5",
                "タグ6",
                "これは20文字を超える非常に長いハッシュタグです",
            ],
        }

        assert validate_template(template, "髪質改善") is False

    def test_validate_template_invalid_hashtag_count(self):
        """ハッシュタグの数が不足している場合のテスト"""
        template = {
            "title": "★髪質改善",
            "menu": "カット+カラー",
            "comment": "コメント",
            "hashtag": ["タグ1", "タグ2"],  # 7個未満
        }

        assert validate_template(template, "髪質改善") is False
