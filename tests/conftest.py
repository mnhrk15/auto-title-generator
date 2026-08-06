import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

# テスト対象のモジュールをインポートできるようにする（app パッケージの import より前に実行する必要がある）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import (  # noqa: E402
    config,
    create_app,
)
from app.featured_keywords import EXTENSION_KEY  # noqa: E402

# ------------------------------------------------------------------
# 共有のテストデータ
# ------------------------------------------------------------------

LADIES_FEATURED = {
    'name': 'くびれヘア特集',
    'keyword': 'くびれヘア',
    'gender': 'ladies',
    'condition': 'スタイル名に「くびれヘア」を含めること',
}

MENS_FEATURED = {
    'name': '韓国風マッシュ特集',
    'keyword': '韓国風マッシュ',
    'gender': 'mens',
    'condition': 'スタイル名に「韓国風マッシュ」を含めること',
}

DEFAULT_SCRAPED_TITLES = [
    'くびれヘアスタイル1',
    'くびれヘアスタイル2',
    'くびれヘアスタイル3',
]

DEFAULT_TEMPLATES = [
    {
        'title': '大人可愛いくびれヘア',
        'menu': 'カット + カラー',
        'comment': '柔らかい質感に仕上げました。',
        'hashtag': ['#くびれヘア', '#大人可愛い'],
    },
    {
        'title': 'トレンドのくびれヘア',
        'menu': 'カット + パーマ',
        'comment': '動きのあるシルエットです。',
        'hashtag': ['#くびれヘア', '#トレンド'],
    },
]


class FakeRepository:
    """FeaturedKeywordsManager の代替。

    リポジトリの実装ではなく「サービス層が依存する 5 メソッドの契約」を満たすことだけを
    目的にしている。MagicMock と違い、返り値の形が実物とずれたらここで気づける。
    """

    def __init__(self, keywords=(), *, available=None, last_error=None, raises=None):
        self._keywords = list(keywords)
        self._by_keyword = {k['keyword'].lower().strip(): k for k in self._keywords}
        # available を明示しなければ「キーワードが1件以上あるか」で判定する（実物と同じ）
        self._available = bool(self._keywords) if available is None else available
        self._last_error = last_error
        # get_all_keywords / is_available が送出する例外。リポジトリ障害の再現用
        self._raises = raises

    def is_available(self):
        if self._raises is not None:
            raise self._raises
        return self._available

    def get_keyword_info(self, keyword):
        if not keyword or not isinstance(keyword, str):
            return None
        return self._by_keyword.get(keyword.lower().strip())

    def get_all_keywords(self):
        if self._raises is not None:
            raise self._raises
        return list(self._keywords)

    def get_last_error(self):
        return self._last_error

    def get_health_status(self):
        return {
            'is_available': self._available,
            'keywords_count': len(self._keywords),
            'file_path': '<fake>',
            'file_exists': True,
            'last_error': str(self._last_error) if self._last_error else None,
            'error_type': type(self._last_error).__name__ if self._last_error else None,
        }


# ------------------------------------------------------------------
# フィクスチャ
# ------------------------------------------------------------------


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
def repository():
    """既定のリポジトリ。ladies / mens を 1 件ずつ持つ。"""
    return FakeRepository([LADIES_FEATURED, MENS_FEATURED])


@pytest.fixture
def app(repository):
    """テスト用 Flask アプリケーション。

    リポジトリは app.extensions 経由で差し替える。get_featured_repository を
    patch する方法と違い、その関数がどのモジュールへ移動しても壊れない。
    """
    app = create_app()
    app.config['TESTING'] = True
    app.extensions[EXTENSION_KEY] = repository
    return app


@pytest.fixture
def client(app):
    """テスト用クライアント"""
    return app.test_client()


@pytest.fixture
def use_repository(app):
    """このテストで使うリポジトリを差し替えるファクトリ。

    tests はパッケージではないため FakeRepository を直接 import できない。
    生成と差し替えをここに閉じ込める。
    """

    def _use(keywords=(), **kwargs):
        repository = FakeRepository(keywords, **kwargs)
        app.extensions[EXTENSION_KEY] = repository
        return repository

    return _use


@pytest.fixture
def fake_pipeline():
    """スクレイパーと生成器を差し替える。

    ここは template_service の内部 import パスを文字列で指すしかないため、
    その文字列がリポジトリ全体でこの 2 行にしか存在しない状態を保つ。
    template_service の import を変えたときの修正箇所がここだけで済む。
    """

    @contextmanager
    def _patch(titles=None, templates=None, scrape_error=None, generate_error=None, unapplied=()):
        scrape = AsyncMock(
            return_value=DEFAULT_SCRAPED_TITLES if titles is None else titles,
            side_effect=scrape_error,
        )
        generate = AsyncMock(
            return_value=(
                DEFAULT_TEMPLATES if templates is None else templates,
                [],
                list(unapplied),
            ),
            side_effect=generate_error,
        )
        with (
            patch(
                'app.services.template_service.HotPepperScraper.scrape_titles_async',
                scrape,
            ),
            patch(
                'app.services.template_service.TemplateGenerator.generate_templates_async',
                generate,
            ),
        ):
            yield generate

    return _patch


@pytest.fixture
def fake_scraper():
    """スクレイパーだけを差し替える。

    生成器は本物を使いたいケース（API キー未設定の扱いなど）で使う。
    """

    @contextmanager
    def _patch(titles=None, error=None):
        with patch(
            'app.services.template_service.HotPepperScraper.scrape_titles_async',
            AsyncMock(
                return_value=DEFAULT_SCRAPED_TITLES if titles is None else titles,
                side_effect=error,
            ),
        ) as scrape:
            yield scrape

    return _patch


@pytest.fixture
def temp_dir():
    """一時ディレクトリ。テスト終了時に削除する。"""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def valid_keywords_data():
    """featured_keywords.json の正常なデータ"""
    return [
        {
            'name': 'テスト用くびれヘア',
            'keyword': 'くびれヘア',
            'gender': 'ladies',
            'condition': 'テスト用の掲載条件です。',
        },
        {
            'name': 'テスト用韓国風マッシュ',
            'keyword': '韓国風マッシュ',
            'gender': 'mens',
            'condition': 'テスト用のメンズ掲載条件です。',
        },
    ]
