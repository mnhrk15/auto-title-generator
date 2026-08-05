"""Gemini レスポンス解釈のテスト。

genai.Client には依存しないので、擬似レスポンスだけでテストできる。
"""

import json
from types import SimpleNamespace

import pytest
from google.genai import types

from app.errors import GenerationError
from app.gemini_response import extract_result
from app.schemas import GeneratedTemplate, GenerationResult, TrendingKeyword


class TestExtractResult:
    """_extract_result メソッドのテスト

    response_schema による構造化出力へ移行したため、旧 TestParseResponse が
    検証していた失敗モード（マークダウン剥がし、前後テキストの混入、
    旧配列形式へのフォールバック、内部配列の誤検出）は構造的に発生しなくなった。
    それらのテストは常に緑になるだけでリグレッション検知能力を持たないため、
    ここでは「構造化出力で実際に起こりうる失敗」だけを検証する。
    """

    @staticmethod
    def _template(title="タイトル"):
        return GeneratedTemplate(title=title, menu="メニュー", comment="コメント", hashtag=["タグ"])

    @staticmethod
    def _response(parsed=None, text=None, finish_reason=types.FinishReason.STOP):
        candidate = SimpleNamespace(finish_reason=finish_reason)
        return SimpleNamespace(
            candidates=[candidate], parsed=parsed, text=text, usage_metadata=None
        )

    def test_uses_parsed_result(self):
        """parsed が返っていればそれをそのまま辞書化して使う"""
        parsed = GenerationResult(
            trending_keywords=[TrendingKeyword(keyword="ウルフカット", count=5, reason="テスト")],
            templates=[self._template("タイトル1"), self._template("タイトル2")],
        )

        templates, trending = extract_result(self._response(parsed=parsed))

        assert [t["title"] for t in templates] == ["タイトル1", "タイトル2"]
        assert trending == [{"keyword": "ウルフカット", "count": 5, "reason": "テスト"}]

    def test_falls_back_to_raw_text(self):
        """parsed が None でも生テキストから復元できる"""
        raw = json.dumps(
            {
                "trending_keywords": [],
                "templates": [
                    {
                        "title": "タイトル1",
                        "menu": "メニュー",
                        "comment": "コメント",
                        "hashtag": ["タグ"],
                    }
                ],
            },
            ensure_ascii=False,
        )

        templates, trending = extract_result(self._response(parsed=None, text=raw))

        assert templates[0]["title"] == "タイトル1"
        assert trending == []

    def test_empty_text_raises(self):
        """parsed も text も無ければ生成エラー"""
        with pytest.raises(GenerationError):
            extract_result(self._response(parsed=None, text=None))

    def test_invalid_json_raises(self):
        with pytest.raises(GenerationError):
            extract_result(self._response(parsed=None, text="これはJSONではない"))

    def test_schema_mismatch_raises(self):
        """スキーマに合わないJSON（hashtag が配列でない）は生成エラー"""
        raw = json.dumps(
            {
                "trending_keywords": [],
                "templates": [
                    {
                        "title": "タイトル",
                        "menu": "メニュー",
                        "comment": "コメント",
                        "hashtag": "タグ1 タグ2",
                    }
                ],
            },
            ensure_ascii=False,
        )

        with pytest.raises(GenerationError):
            extract_result(self._response(parsed=None, text=raw))

    def test_max_tokens_reports_truncation(self):
        """出力上限で打ち切られた場合、原因が分かるメッセージを返す

        以前は finish_reason を見ておらず、途中で切れた JSON の
        パースエラーとしてしか観測できなかった。
        """
        response = self._response(
            parsed=None, text=None, finish_reason=types.FinishReason.MAX_TOKENS
        )

        with pytest.raises(GenerationError) as excinfo:
            extract_result(response)

        assert '長すぎ' in str(excinfo.value)

    def test_no_candidates_raises(self):
        response = SimpleNamespace(candidates=[], parsed=None, text=None)

        with pytest.raises(GenerationError):
            extract_result(response)

    def test_empty_templates_is_extracted_as_empty_list(self):
        """templates が空配列でも _extract_result 自体は成功する

        GenerationResult には最小件数の制約がないためスキーマ検証は通る。
        「0件」の扱いは generate_templates_async 側の責務
        （test_generation_with_no_valid_templates_raises_generation_error）。
        """
        parsed = GenerationResult(trending_keywords=[], templates=[])

        templates, trending = extract_result(self._response(parsed=parsed))

        assert templates == []
        assert trending == []

    def test_null_trending_keywords_is_tolerated(self):
        """trending_keywords が null / 欠落でもテンプレートは失われない

        トレンドキーワードは付随情報でしかないので、これが欠けただけで
        テンプレート20件の生成全体を失敗させてはいけない。
        """
        for payload in (
            {
                "trending_keywords": None,
                "templates": [
                    {
                        "title": "タイトル1",
                        "menu": "メニュー",
                        "comment": "コメント",
                        "hashtag": ["タグ"],
                    }
                ],
            },
            {
                "templates": [
                    {
                        "title": "タイトル1",
                        "menu": "メニュー",
                        "comment": "コメント",
                        "hashtag": ["タグ"],
                    }
                ]
            },
        ):
            raw = json.dumps(payload, ensure_ascii=False)

            templates, trending = extract_result(self._response(parsed=None, text=raw))

            assert templates[0]["title"] == "タイトル1"
            assert trending == []
