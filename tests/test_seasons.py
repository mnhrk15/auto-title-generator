"""季節・カラーキーワードの正規化と付加のテスト。

純粋なロジックなので TemplateGenerator（＝API キー）を必要としない。
"""

import pytest

from app import config
from app.seasons import apply_season_keywords, normalize_seasons


class TestSeasonKeywordAppend:
    """apply_season_keywords のテスト（生成後の季節・カラー付加）"""

    @staticmethod
    def _templates(*titles):
        return [{"title": title} for title in titles]

    @staticmethod
    def _suffix(template, base_length):
        """付加された部分（区切り記号＋キーワード）を返す。未付加なら空文字"""
        return template["title"][base_length:]

    def test_appends_to_short_title(self):
        """26文字未満のタイトルに「◎春カラー」が付加される"""
        templates = self._templates("韓国風くびれレイヤー髪質改善透明感")  # 17文字・記号なし

        apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == "韓国風くびれレイヤー髪質改善透明感◎春カラー"

    def test_skips_long_title(self):
        """26文字以上のタイトルは変更されない"""
        title = "あ" * 26
        templates = self._templates(title)

        apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == title

    def test_threshold_boundary(self):
        """閾値の境界: 25文字は付加され、26文字は付加されない"""
        templates = self._templates("あ" * 25, "あ" * 26)

        apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == "あ" * 25 + "◎春カラー"
        assert len(templates[0]["title"]) == 30
        assert templates[1]["title"] == "あ" * 26

    def test_skips_when_result_exceeds_limit(self):
        """付加すると30文字を超える場合は付加しない"""
        title = "あ" * 22  # 22 + 1 + 9 = 32文字 > 30
        templates = self._templates(title)

        apply_season_keywords(templates, ["bleach_free"])

        assert templates[0]["title"] == title

    def test_appends_longest_keyword_when_it_fits(self):
        """余白が足りていれば長いキーワードも付加される"""
        title = "あ" * 20  # 20 + 1 + 9 = 30文字（ちょうど上限）
        templates = self._templates(title)

        apply_season_keywords(templates, ["bleach_free"])

        assert templates[0]["title"] == f"{title}◎ブリーチなしカラー"
        assert len(templates[0]["title"]) == 30

    def test_distributes_evenly(self):
        """複数選択時は対象タイトルへ均等に配分される"""
        templates = self._templates(*["あ" * 15 for _ in range(6)])

        apply_season_keywords(templates, ["spring", "summer", "autumn"])

        applied = [self._suffix(t, 15)[1:] for t in templates]
        assert applied.count("春カラー") == 2
        assert applied.count("夏カラー") == 2
        assert applied.count("秋カラー") == 2

    def test_long_keyword_is_not_starved(self):
        """余白の限られる長いキーワードが、短いキーワードに枠を奪われないこと"""
        # 20文字のタイトルだけが「ブリーチなしカラー」(9文字) を収められる
        templates = self._templates("あ" * 20, *["あ" * 25 for _ in range(3)])

        apply_season_keywords(templates, ["spring", "bleach_free"])

        assert self._suffix(templates[0], 20)[1:] == "ブリーチなしカラー"
        for template in templates[1:]:
            assert self._suffix(template, 25)[1:] == "春カラー"

    def test_mixed_lengths_distribution(self):
        """タイトル長がばらついていても各キーワードが付加される"""
        base_lengths = [18, 19, 20, 25, 25, 25]
        templates = self._templates(*["あ" * n for n in base_lengths])

        apply_season_keywords(templates, ["spring", "bleach_free"])

        applied = [self._suffix(t, n)[1:] for t, n in zip(templates, base_lengths, strict=True)]
        assert applied.count("ブリーチなしカラー") == 3
        assert applied.count("春カラー") == 3

    def test_distributes_evenly_across_keyword_lengths(self):
        """どのキーワードも全タイトルに収まる場合、長い語に偏らず均等に配分される"""
        templates = self._templates(*["あ" * 15 for _ in range(20)])

        apply_season_keywords(templates, ["spring", "bleach_free"])

        applied = [self._suffix(t, 15)[1:] for t in templates]
        assert applied.count("春カラー") == 10
        assert applied.count("ブリーチなしカラー") == 10

    def test_short_keyword_not_starved_by_long_one(self):
        """付加できるタイトルが少なくても、長い語が全ての枠を奪わない"""
        templates = self._templates("あ" * 14, "あ" * 10)

        apply_season_keywords(templates, ["winter", "bleach_free"])

        applied = {self._suffix(t, n)[1:] for t, n in zip(templates, (14, 10), strict=True)}
        assert applied == {"冬カラー", "ブリーチなしカラー"}

    def test_prefers_keyword_that_fills_the_title(self):
        """余白のあるタイトルには、上限文字数に近づく長いキーワードを優先して付加する"""
        base_lengths = [18, 19, 20, 23, 24, 25]
        templates = self._templates(*["あ" * n for n in base_lengths])

        apply_season_keywords(templates, ["spring", "bleach_free"])

        # 18〜20文字帯にはブリーチなしカラー、23〜25文字帯には春カラーが入り、全て28〜30文字になる
        applied = [self._suffix(t, n)[1:] for t, n in zip(templates, base_lengths, strict=True)]
        assert applied[:3] == ["ブリーチなしカラー"] * 3
        assert applied[3:] == ["春カラー"] * 3
        assert [len(t["title"]) for t in templates] == [28, 29, 30, 28, 29, 30]

    @pytest.mark.parametrize(
        "title,expected",
        [
            # タイトルが使っている区切り記号に合わせる
            ("美髪パーマ/艶髪/レイヤーカット", "美髪パーマ/艶髪/レイヤーカット/春カラー"),
            ("小顔レイヤーボブ×パーマ", "小顔レイヤーボブ×パーマ×春カラー"),
            # 複数種類ある場合は末尾に近いものに合わせる
            ("ふんわりパーマ×ミディアム/艶髪", "ふんわりパーマ×ミディアム/艶髪/春カラー"),
            ("大人可愛いボブ/パーマ×艶髪", "大人可愛いボブ/パーマ×艶髪×春カラー"),
        ],
    )
    def test_separator_matches_title_delimiter(self, title, expected):
        """タイトルがすでに使っている区切り記号に合わせて付加される"""
        templates = self._templates(title)

        apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == expected

    def test_separator_rotates_for_plain_titles(self):
        """記号なしのタイトルには ◎ → / → × の順で記号が割り当てられる"""
        templates = self._templates(*["あ" * 15 for _ in range(4)])

        apply_season_keywords(templates, ["spring"])

        assert [self._suffix(t, 15)[0] for t in templates] == ["◎", "/", "×", "◎"]

    def test_rotation_skips_separator_already_in_title(self):
        """ローテーションはタイトルにすでにある記号を避ける"""
        templates = self._templates("垢抜け◎レイヤーカット")  # ◎ を含むが / × は含まない

        apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == "垢抜け◎レイヤーカット/春カラー"

    def test_skips_duplicate_keyword(self):
        """すでに同じキーワードを含むタイトルには重複付加しない"""
        templates = self._templates("春カラー透明感レイヤー")

        apply_season_keywords(templates, ["spring"])

        assert templates[0]["title"] == "春カラー透明感レイヤー"

    def test_uses_other_keyword_when_duplicated(self):
        """重複するキーワードを避けて別の選択キーワードが使われる"""
        templates = self._templates("春カラー透明感レイヤー")

        apply_season_keywords(templates, ["spring", "summer"])

        assert templates[0]["title"] == "春カラー透明感レイヤー◎夏カラー"

    def test_no_change_without_seasons(self):
        """未選択なら一切変更されない"""
        templates = self._templates("韓国風くびれレイヤー髪質改善透明感")

        apply_season_keywords(templates, [])

        assert templates[0]["title"] == "韓国風くびれレイヤー髪質改善透明感"

    def test_all_titles_within_limit(self):
        """付加後も全タイトルが上限文字数以内に収まる"""

        templates = self._templates(*["あ" * length for length in range(10, 30)])

        apply_season_keywords(templates, ["spring", "summer", "autumn", "winter", "bleach_free"])

        for template in templates:
            assert len(template["title"]) <= config.CHAR_LIMITS["title"]
        # 付加自体は行われている（上限チェックが空振りしていないこと）
        assert sum(len(t["title"]) > n for t, n in zip(templates, range(10, 30), strict=True)) > 0

    def test_returns_empty_when_all_applied(self):
        """全キーワードが付加できたら未付与リストは空"""
        templates = self._templates("あ" * 15)

        unapplied = apply_season_keywords(templates, ["spring"])

        assert unapplied == []

    def test_returns_key_when_no_title_fits(self):
        """全タイトルが閾値以上なら、そのキーワードは未付与として返る"""
        templates = self._templates("あ" * 26, "あ" * 28)

        unapplied = apply_season_keywords(templates, ["spring"])

        assert unapplied == ["spring"]

    def test_returns_only_partially_unapplied_keys(self):
        """付加枠が足りない場合、付加できなかったキーワードだけが返る"""
        # 付加できるタイトルは1件だけ。spring が先に枠を取り、summer が未付与になる
        templates = self._templates("あ" * 15, "あ" * 26)

        unapplied = apply_season_keywords(templates, ["spring", "summer"])

        assert unapplied == ["summer"]

    def test_already_present_keyword_is_not_reported_unapplied(self):
        """付加できなくても既にタイトルに含まれていれば未付与に数えない

        検索キーワード自体が「春カラー」などの場合、全タイトルに含まれて
        重複回避でスキップされるが、ユーザーから見れば「含まれている」。
        """
        templates = self._templates("春カラー透明感レイヤー")

        unapplied = apply_season_keywords(templates, ["spring"])

        assert unapplied == []

    def test_already_present_keyword_is_found_in_any_template(self):
        """既含有の判定は先頭だけでなく全テンプレートを見る"""
        # どちらも閾値以上で付加対象外。キーワードは 2 件目にだけ元から含まれる
        templates = self._templates("あ" * 26, "春カラー" + "あ" * 22)

        unapplied = apply_season_keywords(templates, ["spring"])

        assert unapplied == []

    def test_returns_empty_without_seasons(self):
        """未選択なら未付与リストも空"""
        assert apply_season_keywords(self._templates("あ" * 15), []) == []

    def test_returns_all_keys_for_empty_templates(self):
        """テンプレートが空なら全キーワードが未付与として返る（防御的挙動）"""
        assert apply_season_keywords([], ["spring", "summer"]) == ["spring", "summer"]


class TestNormalizeSeasons:
    def test_normalizes_order_and_removes_unknown_and_duplicates(self):
        assert normalize_seasons(["bleach_free", "spring", "unknown", "spring"], "ladies") == [
            "spring",
            "bleach_free",
        ]

    def test_mens_gets_nothing(self):
        """メンズでは季節カラー／ブリーチなしカラーを扱わない"""
        assert normalize_seasons(["spring"], "mens") == []

    def test_empty_input(self):
        assert normalize_seasons(None, "ladies") == []
        assert normalize_seasons([], "ladies") == []
