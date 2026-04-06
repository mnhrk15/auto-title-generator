import pytest
import json
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

    def test_create_prompt_includes_trend_analysis_section(self, generator):
        """プロンプトにトレンド分析セクションが含まれるかテスト"""
        titles = ["レイヤーカット×ウルフカット透明感", "大人可愛いレイヤーカット小顔"]
        keyword = "レイヤーカット"

        prompt = generator._create_prompt(titles, keyword)

        assert "参照データのトレンド分析" in prompt
        assert "頻繁に組み合わされているキーワード" in prompt
        assert "trending_keywords" in prompt
        assert "文字数制限" in prompt
        assert "常に最優先" in prompt

    def test_create_prompt_trend_analysis_output_format(self, generator):
        """出力形式にtrending_keywordsが指定されているかテスト"""
        titles = ["レイヤーカット×ウルフカット透明感"]
        keyword = "レイヤーカット"

        prompt = generator._create_prompt(titles, keyword)

        assert '"trending_keywords"' in prompt
        assert '"templates"' in prompt
        assert '"count"' in prompt
        assert "trending_keywordsを先に出力し" in prompt


class TestParseResponse:
    """_parse_response メソッドのテスト"""

    @pytest.fixture
    def generator(self):
        return TemplateGenerator()

    def _make_template(self, title="テスト"):
        return {"title": title, "menu": "メニュー", "comment": "コメント", "hashtag": ["タグ"]}

    def test_parse_object_format(self, generator):
        """新形式（オブジェクト形式）の正常パース"""
        data = {
            "trending_keywords": [
                {"keyword": "ウルフカット", "count": 5, "reason": "テスト"}
            ],
            "templates": [self._make_template("タイトル1"), self._make_template("タイトル2")]
        }
        response_text = json.dumps(data, ensure_ascii=False)

        templates, trending = generator._parse_response(response_text)

        assert len(templates) == 2
        assert templates[0]["title"] == "タイトル1"
        assert len(trending) == 1
        assert trending[0]["keyword"] == "ウルフカット"

    def test_parse_array_format_fallback(self, generator):
        """旧形式（配列形式）へのフォールバック"""
        data = [self._make_template("タイトル1"), self._make_template("タイトル2")]
        response_text = json.dumps(data, ensure_ascii=False)

        templates, trending = generator._parse_response(response_text)

        assert len(templates) == 2
        assert templates[0]["title"] == "タイトル1"
        assert trending == []

    def test_parse_markdown_wrapped_json(self, generator):
        """マークダウンコードブロックで囲まれたJSONのパース"""
        data = {
            "trending_keywords": [],
            "templates": [self._make_template("マークダウン内")]
        }
        response_text = f"```json\n{json.dumps(data, ensure_ascii=False)}\n```"

        templates, trending = generator._parse_response(response_text)

        assert len(templates) == 1
        assert templates[0]["title"] == "マークダウン内"

    def test_parse_markdown_wrapped_array(self, generator):
        """マークダウンコードブロックで囲まれた配列形式のパース"""
        data = [self._make_template("配列形式")]
        response_text = f"```json\n{json.dumps(data, ensure_ascii=False)}\n```"

        templates, trending = generator._parse_response(response_text)

        assert len(templates) == 1
        assert templates[0]["title"] == "配列形式"

    def test_parse_object_without_templates_key(self, generator):
        """templatesキーがないオブジェクトの場合はValueErrorを発生"""
        response_text = '{"trending_keywords": [{"keyword": "test"}]}'

        # オブジェクト形式のJSONとしてはパース可能だがtemplatesキーが無いためエラー
        # （以前は配列フォールバックでtrending_keywords内の[]を誤って拾うバグがあった）
        with pytest.raises(ValueError, match="templates"):
            generator._parse_response(response_text)

    def test_parse_invalid_json(self, generator):
        """完全に不正なJSONの場合"""
        response_text = "これはJSONではありません"

        with pytest.raises(ValueError, match="No valid JSON found"):
            generator._parse_response(response_text)

    def test_parse_empty_templates(self, generator):
        """templates が空配列の場合"""
        data = {"trending_keywords": [], "templates": []}
        response_text = json.dumps(data, ensure_ascii=False)

        templates, trending = generator._parse_response(response_text)

        assert templates == []
        assert trending == []

    def test_parse_object_with_surrounding_text(self, generator):
        """JSON前後にテキストがある場合"""
        data = {
            "trending_keywords": [],
            "templates": [self._make_template("前後テキスト")]
        }
        response_text = f"以下がJSONです:\n{json.dumps(data, ensure_ascii=False)}\n以上です。"

        templates, trending = generator._parse_response(response_text)

        assert len(templates) == 1
        assert templates[0]["title"] == "前後テキスト"

    def test_parse_templates_not_list(self, generator):
        """templatesが配列でない場合はValueErrorを発生"""
        response_text = '{"trending_keywords": [], "templates": "invalid"}'

        # templatesが文字列なので有効なリストではない = エラー
        # （以前はフォールバックで[]を誤って拾っていた）
        with pytest.raises(ValueError, match="templates"):
            generator._parse_response(response_text)

    def test_parse_trending_keywords_preserved(self, generator):
        """trending_keywordsの詳細情報が保持されるか"""
        data = {
            "trending_keywords": [
                {"keyword": "韓国風", "count": 10, "reason": "40件中10件"},
                {"keyword": "くびれ", "count": 8, "reason": "40件中8件"}
            ],
            "templates": [self._make_template()]
        }
        response_text = json.dumps(data, ensure_ascii=False)

        templates, trending = generator._parse_response(response_text)

        assert len(trending) == 2
        assert trending[0]["keyword"] == "韓国風"
        assert trending[0]["count"] == 10
        assert trending[1]["keyword"] == "くびれ"

    def test_parse_object_does_not_fallback_to_inner_array(self, generator):
        """オブジェクト形式が壊れていても、内部の配列を拾わないことを確認（リグレッションテスト）"""
        # templates が配列ではなく文字列。trending_keywords 内に配列があるが、
        # 誤ってそれを拾って返してはならない
        response_text = '{"trending_keywords": [{"keyword": "wrong"}], "templates": 42}'

        with pytest.raises(ValueError):
            generator._parse_response(response_text)

    def test_parse_null_trending_keywords(self, generator):
        """trending_keywordsがnullの場合、空リストとして扱う"""
        data = {"trending_keywords": None, "templates": [self._make_template()]}
        response_text = json.dumps(data, ensure_ascii=False)

        templates, trending = generator._parse_response(response_text)

        assert len(templates) == 1
        assert trending == []
