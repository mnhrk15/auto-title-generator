import pytest
from app import create_app
from app.config import JST
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_index_route(client):
    """インデックスページが正しく表示されるかテスト"""
    response = client.get('/')
    assert response.status_code == 200
    assert 'ヘアスタイルタイトルジェネレーター' in response.data.decode('utf-8')

def test_index_shows_maintenance_notice_before_end(client, monkeypatch):
    """メンテナンス終了前: 告知バナーが表示される"""
    notice = {
        'end': datetime.now(JST) + timedelta(days=1),
        'message': 'テスト用メンテナンス告知',
    }
    monkeypatch.setattr('app.main.MAINTENANCE_NOTICE', notice)

    response = client.get('/')
    assert response.status_code == 200
    assert 'テスト用メンテナンス告知' in response.data.decode('utf-8')

def test_index_hides_maintenance_notice_after_end(client, monkeypatch):
    """メンテナンス終了後: 告知バナーが表示されない"""
    notice = {
        'end': datetime.now(JST) - timedelta(days=1),
        'message': 'テスト用メンテナンス告知',
    }
    monkeypatch.setattr('app.main.MAINTENANCE_NOTICE', notice)

    response = client.get('/')
    assert response.status_code == 200
    assert 'テスト用メンテナンス告知' not in response.data.decode('utf-8')

def test_generate_templates_route_success(client):
    """正常系: テンプレート生成が成功するケース"""
    mock_titles = ["★髪質改善トリートメントで艶髪ストレート"]
    mock_templates = [{"title": "★新テンプレート", "menu": "カット+トリートメント", "comment": "サンプルコメント", "hashtag": ["髪質改善"]}]

    with patch('app.main.HotPepperScraper.scrape_titles_async', new_callable=AsyncMock, return_value=mock_titles) as mock_scrape, \
         patch('app.main.TemplateGenerator.generate_templates_async', new_callable=AsyncMock, return_value=(mock_templates, [])) as mock_generate:

        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['templates'] == mock_templates

def test_generate_templates_route_no_keyword(client):
    """キーワードが指定されていない場合のテスト"""
    response = client.post('/api/generate', json={'gender': 'ladies'})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'キーワードを入力してください' in data['error']['message']

def test_generate_templates_route_no_results(client):
    """検索結果が0件の場合のテスト"""
    with patch('app.main.HotPepperScraper.scrape_titles_async', new_callable=AsyncMock, return_value=[]) as mock_scrape:
        response = client.post('/api/generate', json={'keyword': '存在しないキーワード', 'gender': 'ladies'})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert '一致するヘアスタイルが見つかりませんでした' in data['error']['message']

def test_generate_templates_route_generation_error(client):
    """テンプレート生成エラー時のテスト"""
    mock_titles = ["★髪質改善トリートメントで艶髪ストレート"]
    with patch('app.main.HotPepperScraper.scrape_titles_async', new_callable=AsyncMock, return_value=mock_titles) as mock_scrape, \
         patch('app.main.TemplateGenerator.generate_templates_async', new_callable=AsyncMock, side_effect=Exception("Generation failed")) as mock_generate:

        response = client.post('/api/generate', json={'keyword': '髪質改善', 'gender': 'ladies'})
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert '予期せぬエラーが発生しました' in data['error']['message']

def test_generate_templates_route_invalid_json(client):
    """不正なJSONリクエストのテスト"""
    response = client.post('/api/generate', data='invalid json', content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'INVALID_JSON' in data['error']['code']
