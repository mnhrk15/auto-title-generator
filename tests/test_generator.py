import pytest
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from google.genai import types

from app.generator import TemplateGenerator
from app.errors import GenerationError
from app.schemas import GeneratedTemplate, GenerationResult, TrendingKeyword

class TestTemplateGenerator:
    @pytest.fixture
    def generator(self):
        return TemplateGenerator()

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


class TestExtractResult:
    """_extract_result メソッドのテスト

    response_schema による構造化出力へ移行したため、旧 TestParseResponse が
    検証していた失敗モード（マークダウン剥がし、前後テキストの混入、
    旧配列形式へのフォールバック、内部配列の誤検出）は構造的に発生しなくなった。
    それらのテストは常に緑になるだけでリグレッション検知能力を持たないため、
    ここでは「構造化出力で実際に起こりうる失敗」だけを検証する。
    """

    @pytest.fixture
    def generator(self):
        return TemplateGenerator()

    @staticmethod
    def _template(title="タイトル"):
        return GeneratedTemplate(
            title=title, menu="メニュー", comment="コメント", hashtag=["タグ"]
        )

    @staticmethod
    def _response(parsed=None, text=None, finish_reason=types.FinishReason.STOP):
        candidate = SimpleNamespace(finish_reason=finish_reason)
        return SimpleNamespace(
            candidates=[candidate], parsed=parsed, text=text, usage_metadata=None
        )

    def test_uses_parsed_result(self, generator):
        """parsed が返っていればそれをそのまま辞書化して使う"""
        parsed = GenerationResult(
            trending_keywords=[
                TrendingKeyword(keyword="ウルフカット", count=5, reason="テスト")
            ],
            templates=[self._template("タイトル1"), self._template("タイトル2")],
        )

        templates, trending = generator._extract_result(self._response(parsed=parsed))

        assert [t["title"] for t in templates] == ["タイトル1", "タイトル2"]
        assert trending == [{"keyword": "ウルフカット", "count": 5, "reason": "テスト"}]

    def test_falls_back_to_raw_text(self, generator):
        """parsed が None でも生テキストから復元できる"""
        raw = json.dumps({
            "trending_keywords": [],
            "templates": [{
                "title": "タイトル1", "menu": "メニュー",
                "comment": "コメント", "hashtag": ["タグ"],
            }],
        }, ensure_ascii=False)

        templates, trending = generator._extract_result(self._response(parsed=None, text=raw))

        assert templates[0]["title"] == "タイトル1"
        assert trending == []

    def test_empty_text_raises(self, generator):
        """parsed も text も無ければ生成エラー"""
        with pytest.raises(GenerationError):
            generator._extract_result(self._response(parsed=None, text=None))

    def test_invalid_json_raises(self, generator):
        with pytest.raises(GenerationError):
            generator._extract_result(self._response(parsed=None, text="これはJSONではない"))

    def test_schema_mismatch_raises(self, generator):
        """スキーマに合わないJSON（hashtag が配列でない）は生成エラー"""
        raw = json.dumps({
            "trending_keywords": [],
            "templates": [{
                "title": "タイトル", "menu": "メニュー",
                "comment": "コメント", "hashtag": "タグ1 タグ2",
            }],
        }, ensure_ascii=False)

        with pytest.raises(GenerationError):
            generator._extract_result(self._response(parsed=None, text=raw))

    def test_max_tokens_reports_truncation(self, generator):
        """出力上限で打ち切られた場合、原因が分かるメッセージを返す

        以前は finish_reason を見ておらず、途中で切れた JSON の
        パースエラーとしてしか観測できなかった。
        """
        response = self._response(parsed=None, text=None,
                                  finish_reason=types.FinishReason.MAX_TOKENS)

        with pytest.raises(GenerationError) as excinfo:
            generator._extract_result(response)

        assert '長すぎ' in str(excinfo.value)

    def test_no_candidates_raises(self, generator):
        response = SimpleNamespace(candidates=[], parsed=None, text=None)

        with pytest.raises(GenerationError):
            generator._extract_result(response)

    def test_empty_templates_is_extracted_as_empty_list(self, generator):
        """templates が空配列でも _extract_result 自体は成功する

        GenerationResult には最小件数の制約がないためスキーマ検証は通る。
        「0件」の扱いは generate_templates_async 側の責務
        （test_generation_with_no_valid_templates_raises_generation_error）。
        """
        parsed = GenerationResult(trending_keywords=[], templates=[])

        templates, trending = generator._extract_result(self._response(parsed=parsed))

        assert templates == []
        assert trending == []

    def test_null_trending_keywords_is_tolerated(self, generator):
        """trending_keywords が null / 欠落でもテンプレートは失われない

        トレンドキーワードは付随情報でしかないので、これが欠けただけで
        テンプレート20件の生成全体を失敗させてはいけない。
        """
        for payload in (
            {"trending_keywords": None, "templates": [{
                "title": "タイトル1", "menu": "メニュー",
                "comment": "コメント", "hashtag": ["タグ"]}]},
            {"templates": [{
                "title": "タイトル1", "menu": "メニュー",
                "comment": "コメント", "hashtag": ["タグ"]}]},
        ):
            raw = json.dumps(payload, ensure_ascii=False)

            templates, trending = generator._extract_result(
                self._response(parsed=None, text=raw))

            assert templates[0]["title"] == "タイトル1"
            assert trending == []


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
            parsed=parsed, text=None, usage_metadata=None,
        )

        with patch.object(generator.client.aio.models, 'generate_content',
                          new=AsyncMock(return_value=response)):
            with pytest.raises(GenerationError):
                await generator.generate_templates_async(["タイトル"], "髪質改善")
