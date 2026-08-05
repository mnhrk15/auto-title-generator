import json
import logging
from unittest.mock import AsyncMock, patch

import pytest

from app import config, create_app


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
        }
    )
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_setup_logging_is_idempotent():
    """create_app を複数回呼んでもログハンドラが重複登録されない

    本番では asgi.py が create_app() を呼ぶ。以前は app/__init__.py の
    モジュールレベルにも app = create_app() があり、起動のたびにハンドラが
    二重登録されてログが二重出力されていた。
    """
    create_app()
    root_handlers = list(logging.getLogger().handlers)

    create_app()
    create_app()

    assert logging.getLogger().handlers == root_handlers


def test_setup_logging_writes_to_stream():
    """ログがファイルだけでなく標準エラーにも出る

    Render はコンテナの stdout/stderr を収集するため、ストリーム側のハンドラが
    ないとデプロイ後のログがダッシュボードに一切出なくなる。
    """
    create_app()
    handlers = logging.getLogger().handlers

    assert any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in handlers
    ), 'StreamHandler が root に登録されていない'
    assert any(isinstance(h, logging.FileHandler) for h in handlers), (
        'FileHandler が root に登録されていない'
    )


@pytest.mark.parametrize(
    'raw,expected',
    [
        ('true', True),
        ('True', True),
        ('1', True),
        ('yes', True),
        ('on', True),
        ('false', False),
        ('False', False),
        ('0', False),
        ('no', False),
        ('off', False),
        # 解釈できない値は既定値のまま（安全側の既定を黙って壊さない）
        ('', True),
        (' ', True),
        ('enabled', True),
        ('ture', True),
    ],
)
def test_env_bool_falls_back_to_default_on_unknown_value(monkeypatch, raw, expected):
    """真偽値として解釈できない環境変数は既定値を返す

    SCRAPER_VERIFY_SSL のように既定 True が安全側の設定で、書きかけの空文字や
    タイポによって黙って False（＝SSL 検証無効）になってはいけない。
    """
    monkeypatch.setenv('TEST_BOOL_VAR', raw)
    assert config._env_bool('TEST_BOOL_VAR', True) is expected


def test_env_bool_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv('TEST_BOOL_VAR', raising=False)
    assert config._env_bool('TEST_BOOL_VAR', True) is True
    assert config._env_bool('TEST_BOOL_VAR', False) is False


def test_index_route(client):
    """インデックスページが正しく表示されるかテスト"""
    response = client.get('/')
    assert response.status_code == 200
    assert 'ヘアスタイルタイトルジェネレーター' in response.data.decode('utf-8')


def test_generate_templates_route_success(client):
    """正常系: テンプレート生成が成功するケース"""
    mock_titles = ["★髪質改善トリートメントで艶髪ストレート"]
    mock_templates = [
        {
            "title": "★新テンプレート",
            "menu": "カット+トリートメント",
            "comment": "サンプルコメント",
            "hashtag": ["髪質改善"],
        }
    ]

    with (
        patch(
            'app.services.template_service.HotPepperScraper.scrape_titles_async',
            new_callable=AsyncMock,
            return_value=mock_titles,
        ),
        patch(
            'app.services.template_service.TemplateGenerator.generate_templates_async',
            new_callable=AsyncMock,
            return_value=(mock_templates, []),
        ),
    ):
        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['templates'] == mock_templates


def test_generate_response_shape_is_stable(client):
    """/api/generate 成功レスポンスのキー集合が変わっていないこと

    フロントエンド (app/static/js) がこれらのキーに直接依存しているため、
    リファクタリングでレスポンス形状が壊れていないことをここで担保する。
    """
    mock_titles = ["★髪質改善トリートメントで艶髪ストレート"]
    mock_templates = [
        {
            "title": "★新テンプレート",
            "menu": "カット+トリートメント",
            "comment": "サンプルコメント",
            "hashtag": ["髪質改善"],
        }
    ]

    with (
        patch(
            'app.services.template_service.HotPepperScraper.scrape_titles_async',
            new_callable=AsyncMock,
            return_value=mock_titles,
        ),
        patch(
            'app.services.template_service.TemplateGenerator.generate_templates_async',
            new_callable=AsyncMock,
            return_value=(mock_templates, []),
        ),
    ):
        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})

    data = json.loads(response.data)
    assert set(data.keys()) == {
        'success',
        'templates',
        'trending_keywords',
        'is_featured',
        'keyword_type',
        'processing_mode',
        'is_mixed_keyword',
        'original_keyword',
        'featured_keyword_info',
        'processing_summary',
        'status',
    }
    # script.js がテンプレート1件ごとに参照するメタデータ
    assert {
        'is_featured',
        'keyword_type',
        'processing_mode',
        'original_keyword',
        'is_mixed_keyword',
    } <= set(data['templates'][0].keys())


def test_featured_keywords_response_shape_is_stable(client):
    """/api/featured-keywords 成功レスポンスのキー集合が変わっていないこと"""
    response = client.get('/api/featured-keywords?gender=ladies')

    data = json.loads(response.data)
    assert set(data.keys()) == {
        'success',
        'keywords',
        'gender',
        'total_keywords',
        'filtered_keywords',
        'health_status',
        'status',
    }
    # script.js のボタン生成がこの4キーちょうどを前提にしている
    assert data['keywords'], '検証のため特集キーワードが1件以上必要'
    assert set(data['keywords'][0].keys()) == {'name', 'keyword', 'gender', 'condition'}


def test_missing_api_key_is_server_error_not_validation_error(client, monkeypatch):
    """API キー未設定はサーバー設定の不備なので 500 で返す

    以前は generator が ValueError を送出し、それをルートが一律 400
    VALIDATION_ERROR に丸めていたため、ユーザーの入力ミスとして表示されていた。
    """
    from app import config

    settings_without_key = config.get_settings().__class__(
        **{**config.get_settings().__dict__, 'gemini_api_key': None}
    )
    monkeypatch.setattr(config, 'get_settings', lambda: settings_without_key)

    with patch(
        'app.services.template_service.HotPepperScraper.scrape_titles_async',
        new_callable=AsyncMock,
        return_value=["★髪質改善トリートメント"],
    ):
        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})

    assert response.status_code == 500
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'CONFIGURATION_ERROR'


def test_scraping_failure_is_not_reported_as_no_results(client):
    """通信障害は「該当なし」ではなく 502 SCRAPING_ERROR として返す"""
    from app.errors import ScrapingError

    with patch(
        'app.services.template_service.HotPepperScraper.scrape_titles_async',
        new_callable=AsyncMock,
        side_effect=ScrapingError(),
    ):
        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})

    assert response.status_code == 502
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'SCRAPING_ERROR'


def test_generate_templates_route_no_keyword(client):
    """キーワードが指定されていない場合のテスト"""
    response = client.post('/api/generate', json={'gender': 'ladies'})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'キーワードを入力してください' in data['error']['message']


def test_generate_templates_route_no_results(client):
    """検索結果が0件の場合のテスト"""
    with patch(
        'app.services.template_service.HotPepperScraper.scrape_titles_async',
        new_callable=AsyncMock,
        return_value=[],
    ):
        response = client.post(
            '/api/generate', json={'keyword': '存在しないキーワード', 'gender': 'ladies'}
        )
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert '一致するヘアスタイルが見つかりませんでした' in data['error']['message']


def test_generate_templates_route_generation_error(client):
    """テンプレート生成エラー時のテスト"""
    mock_titles = ["★髪質改善トリートメントで艶髪ストレート"]
    with (
        patch(
            'app.services.template_service.HotPepperScraper.scrape_titles_async',
            new_callable=AsyncMock,
            return_value=mock_titles,
        ),
        patch(
            'app.services.template_service.TemplateGenerator.generate_templates_async',
            new_callable=AsyncMock,
            side_effect=Exception("Generation failed"),
        ),
    ):
        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert '予期せぬエラーが発生しました' in data['error']['message']


def test_generate_templates_route_passes_seasons(client):
    """季節・カラー選択が正規化されてジェネレーターに渡されるテスト"""
    mock_titles = ["★髪質改善トリートメントで艶髪ストレート"]
    mock_templates = [
        {
            "title": "★新テンプレート",
            "menu": "カット",
            "comment": "コメント",
            "hashtag": ["髪質改善"],
        }
    ]

    with (
        patch(
            'app.services.template_service.HotPepperScraper.scrape_titles_async',
            new_callable=AsyncMock,
            return_value=mock_titles,
        ),
        patch(
            'app.services.template_service.TemplateGenerator.generate_templates_async',
            new_callable=AsyncMock,
            return_value=(mock_templates, []),
        ) as mock_generate,
    ):
        response = client.post(
            '/api/generate',
            json={
                'keyword': '髪質改善',
                'gender': 'ladies',
                # 定義順と異なる順序・未知の値・重複を含めても正規化される
                'seasons': ['bleach_free', 'unknown', 'spring', 'spring'],
            },
        )
        assert response.status_code == 200
        assert mock_generate.call_args.args[2] == ['spring', 'bleach_free']


def test_generate_templates_route_ignores_seasons_for_mens(client):
    """メンズでは季節・カラー選択が無視されるテスト"""
    mock_titles = ["★メンズマッシュ×ニュアンスパーマ"]
    mock_templates = [
        {"title": "★新テンプレート", "menu": "カット", "comment": "コメント", "hashtag": ["メンズ"]}
    ]

    with (
        patch(
            'app.services.template_service.HotPepperScraper.scrape_titles_async',
            new_callable=AsyncMock,
            return_value=mock_titles,
        ),
        patch(
            'app.services.template_service.TemplateGenerator.generate_templates_async',
            new_callable=AsyncMock,
            return_value=(mock_templates, []),
        ) as mock_generate,
    ):
        response = client.post(
            '/api/generate',
            json={
                'keyword': 'メンズパーマ',
                'gender': 'mens',
                'seasons': ['spring', 'bleach_free'],
            },
        )
        assert response.status_code == 200
        assert mock_generate.call_args.args[2] == []


def test_generate_templates_route_invalid_seasons_type(client):
    """seasons がリスト形式でない場合のテスト"""
    response = client.post(
        '/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies', 'seasons': 'spring'}
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'VALIDATION_ERROR'
    assert '季節・カラーの指定形式' in data['error']['message']


def test_generate_templates_route_invalid_json(client):
    """不正なJSONリクエストのテスト"""
    response = client.post('/api/generate', data='invalid json', content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'INVALID_JSON' in data['error']['code']
