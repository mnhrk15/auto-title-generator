"""エラーレスポンスの形状に関するテスト。

フロントエンド（app/static/js/api.js）は非 2xx でも本文を読み、
error.code を見て案内を切り替える。したがってエラー時にも
JSON が返ること自体が契約であり、ここで担保する。
"""

import json

import pytest

from app.errors import (
    AppError,
    ErrorCode,
    NoResultsError,
    ScrapingError,
    ValidationError,
    error_payload,
)


class TestErrorPayload:
    def test_shape(self):
        payload, status = error_payload('メッセージ', ErrorCode.BAD_REQUEST, 400)

        assert status == 400
        assert payload == {
            'success': False,
            'error': {'message': 'メッセージ', 'code': ErrorCode.BAD_REQUEST},
            'status': 400,
        }

    @pytest.mark.parametrize(
        'error_class,expected_code,expected_status',
        [
            (AppError, ErrorCode.INTERNAL_SERVER_ERROR, 500),
            (ValidationError, ErrorCode.VALIDATION_ERROR, 400),
            (NoResultsError, ErrorCode.NO_RESULTS_FOUND, 404),
            (ScrapingError, ErrorCode.SCRAPING_ERROR, 502),
        ],
    )
    def test_to_payload_uses_class_attributes(self, error_class, expected_code, expected_status):
        payload, status = error_class().to_payload()

        assert status == expected_status
        assert payload['error']['code'] == expected_code
        assert payload['error']['message'] == error_class.DEFAULT_MESSAGE

    def test_explicit_message_overrides_default(self):
        payload, _ = ValidationError('季節の指定が不正です').to_payload()

        assert payload['error']['message'] == '季節の指定が不正です'


class TestHttpErrorResponses:
    def test_unknown_path_returns_json_404(self, client):
        response = client.get('/no-such-path')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == ErrorCode.NOT_FOUND

    def test_wrong_method_is_handled(self, client):
        """GET 専用のエンドポイントに POST した場合"""
        response = client.post('/api/featured-keywords')

        assert response.status_code in (400, 405)

    def test_unexpected_exception_returns_json_500(self, client, fake_scraper):
        """想定外の例外はユーザーに詳細を出さず 500 で返す"""
        with fake_scraper(error=RuntimeError('想定外')):
            response = client.post('/api/generate', json={'keyword': 'ボブ', 'gender': 'ladies'})

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == ErrorCode.INTERNAL_SERVER_ERROR
        # 例外の中身がそのまま漏れていないこと
        assert '想定外' not in data['error']['message']
