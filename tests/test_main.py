import pytest
from app import app
import json
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    """テストクライアントを作成"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """インデックスページが正しく表示されるかテスト"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'<!DOCTYPE html>' in response.data

def test_generate_templates_route_success(client):
    """テンプレート生成エンドポイントの正常系テスト"""
    mock_templates = [
        {
            "title": "★髪質改善×透明感カラー◎艶髪ストレート",
            "menu": "カット+カラー+髪質改善トリートメント",
            "comment": "髪質改善トリートメントで、まとまりのある艶やかな髪へ。",
            "hashtag": "髪質改善,透明感カラー,艶髪"
        }
    ]
    
    with patch('app.scraping.HotPepperScraper.scrape_titles') as mock_scrape:
        with patch('app.generator.TemplateGenerator.generate_templates') as mock_generate:
            # スクレイピングとテンプレート生成のモック
            mock_scrape.return_value = ["★髪質改善トリートメントで艶髪ストレート"]
            mock_generate.return_value = mock_templates
            
            # APIリクエスト
            response = client.post('/generate', json={
                'keyword': '髪質改善'
            })
            
            # レスポンスの検証
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'templates' in data
            assert len(data['templates']) == 1
            template = data['templates'][0]
            assert all(key in template for key in ['title', 'menu', 'comment', 'hashtag'])
            assert '髪質改善' in template['title']

def test_generate_templates_route_no_keyword(client):
    """キーワードが指定されていない場合のテスト"""
    response = client.post('/generate', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'error' in data
    assert 'キーワードを入力してください' in data['error']

def test_generate_templates_route_empty_keyword(client):
    """空のキーワードが指定された場合のテスト"""
    response = client.post('/generate', json={'keyword': ''})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'error' in data
    assert 'キーワードを入力してください' in data['error']

def test_generate_templates_route_no_results(client):
    """検索結果が0件の場合のテスト"""
    with patch('app.scraping.HotPepperScraper.scrape_titles') as mock_scrape:
        mock_scrape.return_value = []
        
        response = client.post('/generate', json={'keyword': '存在しないキーワード'})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
        assert '一致するヘアスタイルが見つかりませんでした' in data['error']

def test_generate_templates_route_scraping_error(client):
    """スクレイピングエラー時のテスト"""
    with patch('app.scraping.HotPepperScraper.scrape_titles') as mock_scrape:
        mock_scrape.side_effect = Exception("Scraping failed")
        
        response = client.post('/generate', json={'keyword': '髪質改善'})
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
        assert 'エラーが発生しました' in data['error']

def test_generate_templates_route_generation_error(client):
    """テンプレート生成エラー時のテスト"""
    with patch('app.scraping.HotPepperScraper.scrape_titles') as mock_scrape:
        with patch('app.generator.TemplateGenerator.generate_templates') as mock_generate:
            mock_scrape.return_value = ["★髪質改善トリートメントで艶髪ストレート"]
            mock_generate.side_effect = Exception("Generation failed")
            
            response = client.post('/generate', json={'keyword': '髪質改善'})
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data
            assert 'エラーが発生しました' in data['error']

def test_generate_templates_route_invalid_json(client):
    """不正なJSONリクエストのテスト"""
    response = client.post('/generate', data='invalid json', content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'error' in data
    assert 'Invalid JSON' in data['error'] 