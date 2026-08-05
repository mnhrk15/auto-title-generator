import json
import logging

import pytest

from app import config, create_app


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


def test_generate_templates_route_success(client, fake_pipeline):
    """正常系: テンプレート生成が成功するケース"""
    mock_templates = [
        {
            "title": "★新テンプレート",
            "menu": "カット+トリートメント",
            "comment": "サンプルコメント",
            "hashtag": ["髪質改善"],
        }
    ]

    with fake_pipeline(templates=mock_templates):
        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['templates'] == mock_templates


def test_generate_response_shape_is_stable(client, fake_pipeline):
    """/api/generate 成功レスポンスのキー集合が変わっていないこと

    フロントエンド (app/static/js) がこれらのキーに直接依存しているため、
    リファクタリングでレスポンス形状が壊れていないことをここで担保する。
    """
    with fake_pipeline():
        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})

    data = json.loads(response.data)
    assert set(data.keys()) == {
        'success',
        'templates',
        'is_featured',
        'featured_keyword_info',
    }
    # app/static/js がテンプレート1件ごとに参照するメタデータ
    assert 'is_featured' in data['templates'][0]


def test_featured_keywords_response_shape_is_stable(client):
    """/api/featured-keywords 成功レスポンスのキー集合が変わっていないこと"""
    response = client.get('/api/featured-keywords?gender=ladies')

    data = json.loads(response.data)
    assert set(data.keys()) == {'success', 'keywords', 'message'}
    # featured-keywords.js のボタン生成がこの4キーちょうどを前提にしている
    assert data['keywords'], '検証のため特集キーワードが1件以上必要'
    assert set(data['keywords'][0].keys()) == {'name', 'keyword', 'gender', 'condition'}


def test_missing_api_key_is_server_error_not_validation_error(client, monkeypatch, fake_scraper):
    """API キー未設定はサーバー設定の不備なので 500 で返す

    以前は generator が ValueError を送出し、それをルートが一律 400
    VALIDATION_ERROR に丸めていたため、ユーザーの入力ミスとして表示されていた。
    """
    from app import config

    settings_without_key = config.get_settings().__class__(
        **{**config.get_settings().__dict__, 'gemini_api_key': None}
    )
    monkeypatch.setattr(config, 'get_settings', lambda: settings_without_key)

    with fake_scraper():
        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})

    assert response.status_code == 500
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'CONFIGURATION_ERROR'


def test_scraping_failure_is_not_reported_as_no_results(client, fake_scraper):
    """通信障害は「該当なし」ではなく 502 SCRAPING_ERROR として返す"""
    from app.errors import ScrapingError

    with fake_scraper(error=ScrapingError()):
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
    assert data['error']['code'] == 'VALIDATION_ERROR'


def test_generate_templates_route_no_results(client, fake_scraper):
    """検索結果が0件の場合のテスト"""
    with fake_scraper(titles=[]):
        response = client.post(
            '/api/generate', json={'keyword': '存在しないキーワード', 'gender': 'ladies'}
        )
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == 'NO_RESULTS_FOUND'


def test_generate_templates_route_generation_error(client, fake_pipeline):
    """テンプレート生成エラー時のテスト"""
    with fake_pipeline(generate_error=Exception("Generation failed")):
        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == 'INTERNAL_SERVER_ERROR'


def test_generate_templates_route_passes_seasons(client, fake_pipeline):
    """季節・カラー選択が正規化されてジェネレーターに渡されるテスト"""
    with fake_pipeline() as mock_generate:
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
        assert mock_generate.call_args.kwargs['seasons'] == ['spring', 'bleach_free']


def test_generate_templates_route_ignores_seasons_for_mens(client, fake_pipeline):
    """メンズでは季節・カラー選択が無視されるテスト"""
    with fake_pipeline() as mock_generate:
        response = client.post(
            '/api/generate',
            json={
                'keyword': 'メンズパーマ',
                'gender': 'mens',
                'seasons': ['spring', 'bleach_free'],
            },
        )
        assert response.status_code == 200
        assert mock_generate.call_args.kwargs['seasons'] == []


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
    assert data['error']['code'] == 'INVALID_JSON'


class TestParseGenerateRequest:
    """リクエストのパースは Flask コンテキスト無しで検証できる"""

    def test_normalizes_seasons(self):
        from app.main import parse_generate_request

        req = parse_generate_request(
            {
                'keyword': '髪質改善',
                'gender': 'ladies',
                # 定義順と異なる順序・未知の値・重複を含めても正規化される
                'seasons': ['bleach_free', 'unknown', 'spring', 'spring'],
            }
        )

        assert req.seasons == ['spring', 'bleach_free']

    def test_drops_seasons_for_mens(self):
        from app.main import parse_generate_request

        req = parse_generate_request(
            {'keyword': 'メンズパーマ', 'gender': 'mens', 'seasons': ['spring']}
        )

        assert req.seasons == []

    @pytest.mark.parametrize('body', [{'keyword': 'ボブ'}, {'keyword': 'ボブ', 'seasons': None}])
    def test_seasons_omitted_or_null_is_empty(self, body):
        from app.main import parse_generate_request

        assert parse_generate_request(body).seasons == []

    def test_defaults(self):
        from app.config import DEFAULT_MODEL
        from app.main import parse_generate_request

        req = parse_generate_request({'keyword': 'ボブ'})

        assert req.gender == 'ladies'
        assert req.seasons == []
        assert req.model == DEFAULT_MODEL

    @pytest.mark.parametrize('body', [[1, 2], 'ただの文字列', 42, None])
    def test_non_object_body_is_invalid_json(self, body):
        """配列や空ボディは以前 500 になっていた（data.get で AttributeError）"""
        from app.errors import InvalidJsonError
        from app.main import parse_generate_request

        with pytest.raises(InvalidJsonError):
            parse_generate_request(body)

    @pytest.mark.parametrize(
        'body',
        [
            {'gender': 'ladies'},  # keyword なし
            {'keyword': ''},  # 空の keyword
            {'keyword': 'ボブ', 'gender': 'invalid'},
            {'keyword': 'ボブ', 'seasons': 'spring'},  # 配列でない
            # falsy な非リスト。`data.get('seasons') or []` と書くと素通りする
            {'keyword': 'ボブ', 'seasons': 0},
            {'keyword': 'ボブ', 'seasons': False},
            {'keyword': 'ボブ', 'seasons': ''},
            {'keyword': 'ボブ', 'seasons': {}},
        ],
    )
    def test_invalid_values(self, body):
        from app.errors import ValidationError
        from app.main import parse_generate_request

        with pytest.raises(ValidationError):
            parse_generate_request(body)


def test_empty_body_returns_400_not_500(client):
    """Content-Type なしの空ボディは 400。以前は get_json() が 415 を投げ 500 になっていた"""
    response = client.post('/api/generate')

    assert response.status_code == 400
    assert json.loads(response.data)['error']['code'] == 'INVALID_JSON'


def test_array_body_returns_400_not_500(client):
    """JSON 配列は 400。以前は data.get の AttributeError で 500 になっていた"""
    response = client.post('/api/generate', json=[1, 2])

    assert response.status_code == 400
    assert json.loads(response.data)['error']['code'] == 'INVALID_JSON'


def test_featured_keywords_invalid_gender_is_rejected(client):
    """不正な性別はサイレントに ladies へ倒さず 400 で返す

    黙って倒すとフロントエンドのバグが表に出なくなる。
    パラメータ自体が無い場合は従来どおり ladies を既定にする。
    """
    response = client.get('/api/featured-keywords?gender=xxx')

    assert response.status_code == 400
    assert json.loads(response.data)['error']['code'] == 'VALIDATION_ERROR'


class TestTemplateContext:
    """テンプレートに渡す値の一元化"""

    def test_season_ui_labels_matches_choices(self):
        """UI ラベルと生成用の付加語でキーが一致していること

        片方だけ増やすと、チェックできるのに生成側が無視する（またはその逆）になる。
        """
        assert list(config.SEASON_UI_LABELS) == list(config.SEASON_COLOR_CHOICES)

    def test_index_renders_char_limits_from_config(self, client):
        """文字数上限がテンプレートに直書きされていないこと"""
        html = client.get('/').data.decode('utf-8')

        assert f'maxlength="{config.CHAR_LIMITS["title"]}"' in html
        assert f'0/{config.CHAR_LIMITS["title"]}' in html
        assert f'（{config.CHAR_LIMITS["menu"]}文字以内）' in html
        # ハッシュタグはタグ1個あたりの上限なので data 属性で渡す
        assert f'data-max-length="{config.CHAR_LIMITS["hashtag"]}"' in html

    def test_index_renders_season_checkboxes(self, client):
        """季節・カラーのチェックボックスが config の定義順に並ぶこと"""
        html = client.get('/').data.decode('utf-8')

        positions = [html.index(f'value="{key}"') for key in config.SEASON_UI_LABELS]
        assert positions == sorted(positions)
        for label in config.SEASON_UI_LABELS.values():
            assert f'>{label}</span>' in html
