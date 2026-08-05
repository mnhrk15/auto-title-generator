"""プロンプト組み立てのユニットテスト。

build_generation_prompt は純関数なので API キーなしでテストできる。

これらの assert はプロンプト文言に厳密に一致させている。緩めると、
プロンプトを別モジュールへ移した際にテキストが壊れていないことを
検証できなくなるため、意図的に厳密なまま維持している。
"""

import pytest

from app.prompts import build_generation_prompt
from app.seasons import normalize_seasons


class TestBuildGenerationPrompt:
    def test_create_prompt(self):
        """プロンプトが正しく生成されるかテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"

        prompt = build_generation_prompt(titles, keyword)

        # プロンプトに必要な要素が含まれているか確認
        assert keyword in prompt
        assert "[\n  \"" + titles[0] + "\"\n]" in prompt
        assert "文字以内" in prompt  # 文字数制限の指示が含まれているか
        assert "JSON形式" in prompt  # 出力形式の指示が含まれているか

    def test_create_prompt_has_no_pv_boost_rules(self):
        """PV向上キーワードの強制配置ルールが撤廃されているかテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"

        prompt = build_generation_prompt(titles, keyword)

        assert "PV向上キーワードの配置ルール" not in prompt
        for season_word in ("春カラー", "夏カラー", "秋カラー", "冬カラー", "ブリーチなしカラー"):
            assert season_word not in prompt

    def test_create_prompt_mens_has_no_season_colors(self):
        """メンズでは季節カラー・ブリーチなしがプロンプトに一切現れないかテスト"""
        titles = ["★メンズマッシュ×ニュアンスパーマ"]
        keyword = "メンズパーマ"

        # 実際のパイプラインと同じく、正規化を通した値を渡す
        # （メンズでは normalize_seasons が空リストにする）
        prompt = build_generation_prompt(
            titles,
            keyword,
            seasons=normalize_seasons(["spring", "bleach_free"], "mens"),
            gender="mens",
        )

        for ng_word in ("春カラー", "夏カラー", "秋カラー", "冬カラー", "ブリーチなし", "ブリーチ"):
            assert ng_word not in prompt
        # メンズ固有の語彙指示は維持されている
        assert "メンズ特有キーワードの活用" in prompt

    def test_create_prompt_ladies_has_no_season_words(self):
        """レディースでもプロンプトに季節語を注入しない（付加は後処理のみ）"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]
        keyword = "髪質改善"

        prompt = build_generation_prompt(titles, keyword, seasons=["spring"], gender="ladies")

        assert "春カラー" not in prompt

    @pytest.mark.parametrize(
        "seasons,expected_rule,expected_rest",
        [
            # 「春カラー」(4文字)+区切り1文字 → 25文字までが目標帯、幅2で23〜25文字
            (["spring"], "20個中**4個は23〜25文字**", 16),
            (["spring", "summer"], "20個中**8個は23〜25文字**", 12),
            # 「ブリーチなしカラー」(9文字)+区切り1文字 → 20文字までが目標帯
            (["bleach_free"], "20個中**4個は18〜20文字**", 16),
            # 語の長さが異なる場合は帯を分ける（長いタイトル帯から順に提示）
            (["winter", "bleach_free"], "20個中**4個は23〜25文字**、**4個は18〜20文字**", 12),
            # 5つ選択時は1つあたりの枠が2に減り、合計10個に収まる
            (
                ["spring", "summer", "autumn", "winter", "bleach_free"],
                "20個中**8個は23〜25文字**、**2個は18〜20文字**",
                10,
            ),
        ],
    )
    def test_create_prompt_short_title_slots(self, seasons, expected_rule, expected_rest):
        """季節・カラー選択時に、付加後に上限文字数へ届く目標帯が指示されるかテスト"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]

        prompt = build_generation_prompt(titles, "髪質改善", seasons=seasons, gender="ladies")

        assert f"- title: {expected_rule}、残りの{expected_rest}個は**25〜28文字**を目標" in prompt
        assert "後から語句を追記するための余白" in prompt
        assert "上限側に寄せて" in prompt
        # 文字数目標の記述が矛盾しないこと（無条件の25〜28文字指定が残っていない）
        assert "- title: **25〜28文字**を目標" not in prompt

    def test_create_prompt_no_short_slots_without_seasons(self):
        """季節・カラー未選択なら短尺タイトル枠の指示は入らない"""
        titles = ["★髪質改善トリートメントで艶髪ストレート"]

        prompt = build_generation_prompt(titles, "髪質改善")

        assert "後から語句を追記するための余白" not in prompt
        assert "- title: **25〜28文字**を目標" in prompt

    def test_create_prompt_no_short_slots_for_mens(self):
        """メンズは seasons を選んでも短尺タイトル枠の指示は入らない

        normalize_seasons がメンズの選択を落とすので、プロンプト側には空が届く。
        """
        titles = ["★メンズマッシュ×ニュアンスパーマ"]

        prompt = build_generation_prompt(
            titles,
            "メンズパーマ",
            seasons=normalize_seasons(["spring"], "mens"),
            gender="mens",
        )

        assert "後から語句を追記するための余白" not in prompt
        assert "- title: **25〜28文字**を目標" in prompt

    def test_create_prompt_includes_trend_analysis_section(self):
        """プロンプトにトレンド分析セクションが含まれるかテスト"""
        titles = ["レイヤーカット×ウルフカット透明感", "大人可愛いレイヤーカット小顔"]
        keyword = "レイヤーカット"

        prompt = build_generation_prompt(titles, keyword)

        assert "参照データのトレンド分析" in prompt
        assert "頻繁に組み合わされているキーワード" in prompt
        assert "trending_keywords" in prompt
        assert "文字数制限" in prompt
        assert "常に最優先" in prompt

    def test_create_prompt_trend_analysis_output_format(self):
        """出力形式にtrending_keywordsが指定されているかテスト"""
        titles = ["レイヤーカット×ウルフカット透明感"]
        keyword = "レイヤーカット"

        prompt = build_generation_prompt(titles, keyword)

        assert '"trending_keywords"' in prompt
        assert '"templates"' in prompt
        assert '"count"' in prompt
        assert "trending_keywordsを先に出力し" in prompt


class TestFeaturedInstruction:
    """特集キーワード分岐のテスト

    この分岐は featured / mixed / スキップ の3経路があり、
    生成品質に直結するにもかかわらず検証が無かったため追加した。
    """

    TITLES = ["★髪質改善トリートメントで艶髪ストレート"]
    KEYWORD = "ダークパープル"
    FEATURED = {
        "name": "ダークパープル特集",
        "keyword": "ダークパープル",
        "gender": "ladies",
        "condition": "スタイル名に以下の文言が入っていること 「ダークパープル」",
    }

    def _prompt(self, featured_info=FEATURED, context=None):
        return build_generation_prompt(
            self.TITLES,
            self.KEYWORD,
            featured_info=featured_info,
            generation_context=context,
        )

    def test_featured_condition_is_embedded(self):
        """純粋な特集キーワードでは条件文がそのまま埋め込まれる"""
        prompt = self._prompt(
            context={'keyword_type': 'featured', 'original_keyword': self.KEYWORD}
        )

        assert "【重要】特集掲載条件の厳守" in prompt
        assert self.FEATURED["condition"] in prompt
        assert f"このキーワード「{self.KEYWORD}」は今月の特集キーワードです。" in prompt
        # 混在用の文言は出さない
        assert "混在キーワード処理" not in prompt

    def test_mixed_keyword_uses_original_keyword_and_name(self):
        """混在キーワードでは入力全体と特集名の双方が出る"""
        prompt = self._prompt(
            context={'keyword_type': 'mixed', 'original_keyword': 'ダークパープル ボブ'}
        )

        assert "【重要】特集掲載条件の厳守（混在キーワード処理）" in prompt
        assert "入力されたキーワード「ダークパープル ボブ」" in prompt
        assert f"特集キーワード「{self.FEATURED['name']}」が含まれています" in prompt
        assert self.FEATURED["condition"] in prompt

    def test_no_featured_info_omits_the_section(self):
        """特集情報が無ければ特集ブロックは出ない"""
        prompt = self._prompt(featured_info=None)

        assert "特集掲載条件" not in prompt
        # 通常のプロンプトとしては成立している
        assert self.KEYWORD in prompt

    @pytest.mark.parametrize(
        "bad_info",
        [
            "文字列",
            ["リスト"],
            {"name": "条件なし"},  # condition 欠落
            {"name": "条件が空", "condition": ""},  # condition が空
        ],
    )
    def test_malformed_featured_info_is_skipped_without_raising(self, bad_info):
        """特集情報が壊れていても例外にせず、特集ブロックを省いて継続する"""
        prompt = self._prompt(featured_info=bad_info)

        assert "特集掲載条件" not in prompt
        assert self.KEYWORD in prompt

    def test_long_condition_is_truncated(self):
        """条件文が上限を超える場合は切り詰めたうえで埋め込む"""
        from app import config

        long_condition = "あ" * (config.FEATURED_CONDITION_MAX + 50)
        prompt = self._prompt(featured_info={**self.FEATURED, "condition": long_condition})

        assert "あ" * config.FEATURED_CONDITION_MAX + "..." in prompt
        assert long_condition not in prompt

    def test_mixed_falls_back_to_keyword_when_name_missing(self):
        """特集名が無い場合はキーワードで代替する（KeyError にしない）"""
        prompt = self._prompt(
            featured_info={"condition": self.FEATURED["condition"]},
            context={'keyword_type': 'mixed', 'original_keyword': 'ダークパープル ボブ'},
        )

        assert f"特集キーワード「{self.KEYWORD}」が含まれています" in prompt


class TestPromptTargetsMatchConfig:
    """目標帯の補間が config と一致していることのテスト

    title 以外は補間結果を検証していなかったため、config を書き換えたときに
    プロンプト文言との整合が崩れても気づけなかった。
    """

    def test_targets_are_interpolated_from_config(self):
        from app import config

        prompt = build_generation_prompt(["タイトル"], "髪質改善")

        assert f"{config.MENU_TARGET[0]}〜{config.MENU_TARGET[1]}文字" in prompt
        assert f"{config.COMMENT_TARGET[0]}〜{config.COMMENT_TARGET[1]}文字" in prompt
        assert f"{config.TITLE_TARGET[0]}〜{config.TITLE_TARGET[1]}文字" in prompt
        assert f"{config.HASHTAG_MIN_COUNT}個以上" in prompt
