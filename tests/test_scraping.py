import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.scraping import HotPepperScraper
import aiohttp

@pytest.mark.asyncio
class TestHotPepperScraper:
    @pytest.fixture
    def scraper(self):
        return HotPepperScraper()

    async def test_scrape_titles_success(self, scraper):
        """正常系: タイトルの取得が成功するケース"""
        mock_html_page1 = '''
        <html><body>
            <div id="jsiHoverAlphaLayerScope">
                <li><div class="mT5"><a><p><span>タイトル1</span></p></a></div></li>
            </div>
            <div id="searchList">
                <div>dummy</div>
                <div><div class="pT5 pr cFix"><div><ul><li class="pa top0 right0 afterPage"><a href="#">次へ</a></li></ul></div></div></div>
            </div>
        </body></html>
        '''
        mock_html_page2 = '''
        <html><body>
            <div id="jsiHoverAlphaLayerScope">
                <li><div class="mT5"><a><p><span>タイトル2</span></p></a></div></li>
            </div>
        </body></html>
        '''

        # aiohttp.ClientSession.get のレスポンスをモック
        mock_response_p1 = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response_p1.status = 200
        mock_response_p1.text.return_value = mock_html_page1
        mock_response_p1.raise_for_status = MagicMock()

        mock_response_p2 = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response_p2.status = 200
        mock_response_p2.text.return_value = mock_html_page2
        mock_response_p2.raise_for_status = MagicMock()

        # async context managerとしてモック（session.get()はasync withで使われる）
        mock_cm_p1 = MagicMock()
        mock_cm_p1.__aenter__ = AsyncMock(return_value=mock_response_p1)
        mock_cm_p1.__aexit__ = AsyncMock(return_value=False)

        mock_cm_p2 = MagicMock()
        mock_cm_p2.__aenter__ = AsyncMock(return_value=mock_response_p2)
        mock_cm_p2.__aexit__ = AsyncMock(return_value=False)

        mock_get = MagicMock(side_effect=[mock_cm_p1, mock_cm_p2])

        with patch('aiohttp.ClientSession.get', mock_get):
            async with scraper:
                titles = await scraper.scrape_titles_async("キーワード", max_pages=2)

        assert titles == ["タイトル1", "タイトル2"]
        assert mock_get.call_count == 2

    async def test_scrape_titles_no_results(self, scraper):
        """異常系: 検索結果が0件の場合"""
        mock_html = '<html><body><div id="jsiHoverAlphaLayerScope"></div></body></html>'

        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_response.text.return_value = mock_html
        mock_response.raise_for_status = MagicMock()

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch('aiohttp.ClientSession.get', MagicMock(return_value=mock_cm)):
            async with scraper:
                titles = await scraper.scrape_titles_async("存在しないキーワード", max_pages=1)

        assert len(titles) == 0

    async def test_scrape_titles_http_error(self, scraper):
        """異常系: HTTPエラーの場合"""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 404
        # raise_for_statusが呼び出されたときにエラーを発生させる
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=404)

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch('aiohttp.ClientSession.get', MagicMock(return_value=mock_cm)):
            async with scraper:
                titles = await scraper.scrape_titles_async("test", max_pages=1)

        # エラーが発生しても空のリストが返ることを期待
        assert len(titles) == 0

    async def test_async_context_manager(self):
        """非同期コンテキストマネージャの動作確認"""
        # __aenter__でセッションが作成され、__aexit__でclose()が呼ばれることを確認
        with patch('aiohttp.ClientSession') as mock_session_class, \
             patch('aiohttp.TCPConnector'):
            mock_session_instance = MagicMock()
            mock_session_instance.close = AsyncMock()
            mock_session_class.return_value = mock_session_instance

            scraper = HotPepperScraper()
            async with scraper:
                assert scraper.session is mock_session_instance
                mock_session_class.assert_called_once()

            mock_session_instance.close.assert_called_once()
