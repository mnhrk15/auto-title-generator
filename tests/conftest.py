import os
import sys

import pytest

# テスト対象のモジュールをインポートできるようにする（app パッケージの import より前に実行する必要がある）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import (
    config,  # noqa: E402
    create_app,  # noqa: E402
)


@pytest.fixture(autouse=True)
def setup_test_env(request, monkeypatch):
    """テスト用の環境変数を差し込み、設定キャッシュをテストごとに作り直す。

    Settings は get_settings() の初回呼び出し時に環境変数から生成されるため、
    monkeypatch.setenv の後に reset_settings() を挟めば差し替えが効く。
    load_dotenv は既存の環境変数を上書きしないので、.env の有無に関わらず
    ここで設定した値が優先される。

    integration マーカーが付いたテストは実 API を呼ぶため、
    ダミーキーで上書きせず .env / 環境変数の実値をそのまま使う。
    """
    if not request.node.get_closest_marker('integration'):
        monkeypatch.setenv('GEMINI_API_KEY', 'test_api_key')
        monkeypatch.setenv('SCRAPING_DELAY_MIN', '0')
        monkeypatch.setenv('SCRAPING_DELAY_MAX', '0')
        monkeypatch.setenv('MAX_PAGES', '3')

    config.reset_settings()
    yield
    config.reset_settings()


@pytest.fixture
def client():
    """テスト用クライアントを作成"""
    app = create_app()
    app.config.update(
        {
            'TESTING': True,
        }
    )

    with app.test_client() as client:
        yield client
