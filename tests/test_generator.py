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

    def test_create_prompt_has_no_pv_boost_rules(self, generator):
        """PV向上キーワードの強制配置ルールが撤廃されているかテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"

        prompt = generator._create_prompt(titles, keyword)

        assert "PV向上キーワードの配置ルール" not in prompt
        for season_word in ("春カラー", "夏カラー", "秋カラー", "冬カラー", "ブリーチなしカラー"):
            assert season_word not in prompt

    def test_create_prompt_mens_has_no_season_colors(self, generator):
        """メンズでは季節カラー・ブリーチなしがプロンプトに一切現れないかテスト"""
        titles = ["★メンズマッシュ×ニュアンスパーマ"]
        keyword = "メンズパーマ"

        prompt = generator._create_prompt(
            titles, keyword, seasons=["spring", "bleach_free"], gender="mens"
        )

        for ng_word in ("春カラー", "夏カラー", "秋カラー", "冬カラー", "ブリーチなし", "ブリーチ"):
            assert ng_word not in prompt
        # メンズ固有の語彙指示は維持されている
        assert "メンズ特有キーワードの活用" in prompt

    def test_create_prompt_ladies_has_no_season_words(self, generator):
        """レディースでもプロンプトに季節語を注入しない（付加は後処理のみ）"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"

        prompt = generator._create_prompt(titles, keyword, seasons=["spring"], gender="ladies")

        assert "春カラー" not in prompt

    @pytest.mark.parametrize("seasons,expected_rule,expected_rest", [
        # 「春カラー」(4文字)+区切り1文字 → 25文字までが目標帯、幅2で23〜25文字
        (["spring"], "20個中**4個は23〜25文字**", 16),
        (["spring", "summer"], "20個中**8個は23〜25文字**", 12),
        # 「ブリーチなしカラー」(9文字)+区切り1文字 → 20文字までが目標帯
        (["bleach_free"], "20個中**4個は18〜20文字**", 16),
        # 語の長さが異なる場合は帯を分ける（長いタイトル帯から順に提示）
        (["winter", "bleach_free"], "20個中**4個は23〜25文字**、**4個は18〜20文字**", 12),
        # 5つ選択時は1つあたりの枠が2に減り、合計10個に収まる
        (["spring", "summer", "autumn", "winter", "bleach_free"],
         "20個中**8個は23〜25文字**、**2個は18〜20文字**", 10),
    ])
    def test_create_prompt_short_title_slots(self, generator, seasons, expected_rule, expected_rest):
        """季節・カラー選択時に、付加後に上限文字数へ届く目標帯が指示されるかテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]

        prompt = generator._create_prompt(titles, "髪質改善", seasons=seasons, gender="ladies")

        assert f"- title: {expected_rule}、残りの{expected_rest}個は**25〜28文字**を目標" in prompt
        assert "後から語句を追記するための余白" in prompt
        assert "上限側に寄せて" in prompt
        # 文字数目標の記述が矛盾しないこと（無条件の25〜28文字指定が残っていない）
        assert "- title: **25〜28文字**を目標" not in prompt

    def test_create_prompt_no_short_slots_without_seasons(self, generator):
        """季節・カラー未選択なら短尺タイトル枠の指示は入らない"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]

        prompt = generator._create_prompt(titles, "髪質改善")

        assert "後から語句を追記するための余白" not in prompt
        assert "- title: **25〜28文字**を目標" in prompt

    def test_create_prompt_no_short_slots_for_mens(self, generator):
        """メンズは seasons を渡しても短尺タイトル枠の指示は入らない"""
        titles = ["★メンズマッシュ×ニュアンスパーマ"]

        prompt = generator._create_prompt(
            titles, "メンズパーマ", seasons=["spring"], gender="mens"
        )

        assert "後から語句を追記するための余白" not in prompt
        assert "- title: **25〜28文字**を目標" in prompt

    def test_normalize_seasons(self, generator):
        """季節・カラー選択値の正規化テスト"""
        # config の定義順に並び替え、未知値と重複を除去する
        assert generator._normalize_seasons(
            ["bleach_free", "spring", "unknown", "spring"], "ladies"
        ) == ["spring", "bleach_free"]
        # メンズは常に空
        assert generator._normalize_seasons(["spring"], "mens") == []
        # 未指定は空
        assert generator._normalize_seasons(None, "ladies") == []
        assert generator._normalize_seasons([], "ladies") == []

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


class TestSeasonKeywordAppend:
    """_apply_season_keywords メソッドのテスト（生成後の季節・カラー付加）"""

    @pytest.fixture
    def generator(self):
        return TemplateGenerator()

    @staticmethod
    def _templates(*titles):
        return [{"title": title} for title in titles]

    @staticmethod
    def _suffix(template, base_length):
        """付加された部分（区切り記号＋キーワード）を返す。未付加なら空文字"""
        return template["title"][base_length:]

    def test_appends_to_short_title(self, generator):
        """26文字未満のタイトルに「◎春カラー」が付加される"""
        templates = self._templates("韓国風くびれレイヤー髪質改善透明感")  # 17文字・記号なし

        generator._apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == "韓国風くびれレイヤー髪質改善透明感◎春カラー"

    def test_skips_long_title(self, generator):
        """26文字以上のタイトルは変更されない"""
        title = "あ" * 26
        templates = self._templates(title)

        generator._apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == title

    def test_threshold_boundary(self, generator):
        """閾値の境界: 25文字は付加され、26文字は付加されない"""
        templates = self._templates("あ" * 25, "あ" * 26)

        generator._apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == "あ" * 25 + "◎春カラー"
        assert len(templates[0]["title"]) == 30
        assert templates[1]["title"] == "あ" * 26

    def test_skips_when_result_exceeds_limit(self, generator):
        """付加すると30文字を超える場合は付加しない"""
        title = "あ" * 22  # 22 + 1 + 9 = 32文字 > 30
        templates = self._templates(title)

        generator._apply_season_keywords(templates, ["bleach_free"])

        assert templates[0]["title"] == title

    def test_appends_longest_keyword_when_it_fits(self, generator):
        """余白が足りていれば長いキーワードも付加される"""
        title = "あ" * 20  # 20 + 1 + 9 = 30文字（ちょうど上限）
        templates = self._templates(title)

        generator._apply_season_keywords(templates, ["bleach_free"])

        assert templates[0]["title"] == f"{title}◎ブリーチなしカラー"
        assert len(templates[0]["title"]) == 30

    def test_distributes_evenly(self, generator):
        """複数選択時は対象タイトルへ均等に配分される"""
        templates = self._templates(*["あ" * 15 for _ in range(6)])

        generator._apply_season_keywords(templates, ["spring", "summer", "autumn"])

        applied = [self._suffix(t, 15)[1:] for t in templates]
        assert applied.count("春カラー") == 2
        assert applied.count("夏カラー") == 2
        assert applied.count("秋カラー") == 2

    def test_long_keyword_is_not_starved(self, generator):
        """余白の限られる長いキーワードが、短いキーワードに枠を奪われないこと"""
        # 20文字のタイトルだけが「ブリーチなしカラー」(9文字) を収められる
        templates = self._templates("あ" * 20, *["あ" * 25 for _ in range(3)])

        generator._apply_season_keywords(templates, ["spring", "bleach_free"])

        assert self._suffix(templates[0], 20)[1:] == "ブリーチなしカラー"
        for template in templates[1:]:
            assert self._suffix(template, 25)[1:] == "春カラー"

    def test_mixed_lengths_distribution(self, generator):
        """タイトル長がばらついていても各キーワードが付加される"""
        base_lengths = [18, 19, 20, 25, 25, 25]
        templates = self._templates(*["あ" * n for n in base_lengths])

        generator._apply_season_keywords(templates, ["spring", "bleach_free"])

        applied = [self._suffix(t, n)[1:] for t, n in zip(templates, base_lengths)]
        assert applied.count("ブリーチなしカラー") == 3
        assert applied.count("春カラー") == 3

    def test_distributes_evenly_across_keyword_lengths(self, generator):
        """どのキーワードも全タイトルに収まる場合、長い語に偏らず均等に配分される"""
        templates = self._templates(*["あ" * 15 for _ in range(20)])

        generator._apply_season_keywords(templates, ["spring", "bleach_free"])

        applied = [self._suffix(t, 15)[1:] for t in templates]
        assert applied.count("春カラー") == 10
        assert applied.count("ブリーチなしカラー") == 10

    def test_short_keyword_not_starved_by_long_one(self, generator):
        """付加できるタイトルが少なくても、長い語が全ての枠を奪わない"""
        templates = self._templates("あ" * 14, "あ" * 10)

        generator._apply_season_keywords(templates, ["winter", "bleach_free"])

        applied = {self._suffix(t, n)[1:] for t, n in zip(templates, (14, 10))}
        assert applied == {"冬カラー", "ブリーチなしカラー"}

    def test_prefers_keyword_that_fills_the_title(self, generator):
        """余白のあるタイトルには、上限文字数に近づく長いキーワードを優先して付加する"""
        base_lengths = [18, 19, 20, 23, 24, 25]
        templates = self._templates(*["あ" * n for n in base_lengths])

        generator._apply_season_keywords(templates, ["spring", "bleach_free"])

        # 18〜20文字帯にはブリーチなしカラー、23〜25文字帯には春カラーが入り、全て28〜30文字になる
        applied = [self._suffix(t, n)[1:] for t, n in zip(templates, base_lengths)]
        assert applied[:3] == ["ブリーチなしカラー"] * 3
        assert applied[3:] == ["春カラー"] * 3
        assert [len(t["title"]) for t in templates] == [28, 29, 30, 28, 29, 30]

    @pytest.mark.parametrize("title,expected", [
        # タイトルが使っている区切り記号に合わせる
        ("美髪パーマ/艶髪/レイヤーカット", "美髪パーマ/艶髪/レイヤーカット/春カラー"),
        ("小顔レイヤーボブ×パーマ", "小顔レイヤーボブ×パーマ×春カラー"),
        # 複数種類ある場合は末尾に近いものに合わせる
        ("ふんわりパーマ×ミディアム/艶髪", "ふんわりパーマ×ミディアム/艶髪/春カラー"),
        ("大人可愛いボブ/パーマ×艶髪", "大人可愛いボブ/パーマ×艶髪×春カラー"),
    ])
    def test_separator_matches_title_delimiter(self, generator, title, expected):
        """タイトルがすでに使っている区切り記号に合わせて付加される"""
        templates = self._templates(title)

        generator._apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == expected

    def test_separator_rotates_for_plain_titles(self, generator):
        """記号なしのタイトルには ◎ → / → × の順で記号が割り当てられる"""
        templates = self._templates(*["あ" * 15 for _ in range(4)])

        generator._apply_season_keywords(templates, ["spring"])

        assert [self._suffix(t, 15)[0] for t in templates] == ["◎", "/", "×", "◎"]

    def test_rotation_skips_separator_already_in_title(self, generator):
        """ローテーションはタイトルにすでにある記号を避ける"""
        templates = self._templates("垢抜け◎レイヤーカット")  # ◎ を含むが / × は含まない

        generator._apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == "垢抜け◎レイヤーカット/春カラー"

    def test_skips_duplicate_keyword(self, generator):
        """すでに同じキーワードを含むタイトルには重複付加しない"""
        templates = self._templates("春カラー透明感レイヤー")

        generator._apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == "春カラー透明感レイヤー"

    def test_uses_other_keyword_when_duplicated(self, generator):
        """重複するキーワードを避けて別の選択キーワードが使われる"""
        templates = self._templates("春カラー透明感レイヤー")

        generator._apply_season_keywords(templates, ["spring", "summer"])

        assert templates[0]["title"] == "春カラー透明感レイヤー◎夏カラー"

    def test_no_change_without_seasons(self, generator):
        """未選択なら一切変更されない"""
        templates = self._templates("韓国風くびれレイヤー髪質改善透明感")

        generator._apply_season_keywords(templates, [])

        assert templates[0]["title"] == "韓国風くびれレイヤー髪質改善透明感"

    def test_all_titles_within_limit(self, generator):
        """付加後も全タイトルが上限文字数以内に収まる"""
        from app import config

        templates = self._templates(*[
            "あ" * length for length in range(10, 30)
        ])

        generator._apply_season_keywords(
            templates, ["spring", "summer", "autumn", "winter", "bleach_free"]
        )

        for template in templates:
            assert len(template["title"]) <= config.CHAR_LIMITS["title"]
        # 付加自体は行われている（上限チェックが空振りしていないこと）
        assert sum(len(t["title"]) > n for t, n in zip(templates, range(10, 30))) > 0


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
