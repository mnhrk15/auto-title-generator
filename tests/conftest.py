import pytest
import os
import sys
from flask import Flask
from app import create_app

# テスト対象のモジュールをインポートできるようにする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# テスト用の環境変数を設定
@pytest.fixture(autouse=True)
def setup_test_env():
    os.environ['GEMINI_API_KEY'] = 'test_api_key'
    os.environ['SCRAPING_DELAY_MIN'] = '0'
    os.environ['SCRAPING_DELAY_MAX'] = '0'
    os.environ['MAX_PAGES'] = '3'
    yield
    # テスト後にクリーンアップ
    for key in ['GEMINI_API_KEY', 'SCRAPING_DELAY_MIN', 'SCRAPING_DELAY_MAX', 'MAX_PAGES']:
        os.environ.pop(key, None)
        
@pytest.fixture
def client():
    """テスト用クライアントを作成"""
    app = create_app()
    app.config.update({
        'TESTING': True,
    })
    
    with app.test_client() as client:
        yield client 