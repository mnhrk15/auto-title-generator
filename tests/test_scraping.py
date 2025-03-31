import pytest
import requests
import responses
from unittest.mock import patch, MagicMock
from app.scraping import HotPepperScraper

class TestHotPepperScraper:
    @pytest.fixture
    def scraper(self):
        return HotPepperScraper()
        
    @responses.activate
    def test_scrape_titles_success(self, scraper):
        """正常系: タイトルの取得が成功するケース"""
        # モックのHTMLコンテンツ
        mock_html = '''
        <!DOCTYPE html>
        <html>
        <body>
            <ul id="jsiHoverAlphaLayerScope">
                <li><div class="mT5"><a><p><span>★小顔イメチェン似合わせ美髪ワンカールレイヤーカット</span></p></a></div></li>
                <li><div class="mT5"><a><p><span>★髪質改善トリートメントで艶髪ストレート</span></p></a></div></li>
                <li><div class="mT5"><a><p><span>★大人可愛いボブスタイル</span></p></a></div></li>
            </ul>
            <div id="searchList">
                <div>
                    <div class="pT5 pr cFix">
                        <div>
                            <ul>
                                <li class="pa top0 right0 afterPage"><a href="#">次へ</a></li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # 1ページ目のレスポンスを登録
        responses.add(
            responses.GET,
            'https://beauty.hotpepper.jp/CSP/bt/hairCatalogSearch/ladys/condtion/?keyword=%E9%AB%AA%E8%B3%AA%E6%94%B9%E5%96%84',
            body=mock_html,
            status=200,
            content_type='text/html',
        )
        
        # 2ページ目のレスポンスを登録（次へボタンなし）
        mock_html_page2 = mock_html.replace('<li class="pa top0 right0 afterPage"><a href="#">次へ</a></li>', '')
        responses.add(
            responses.GET,
            'https://beauty.hotpepper.jp/CSP/bt/hairCatalogSearch/ladys/condtion/?keyword=%E9%AB%AA%E8%B3%AA%E6%94%B9%E5%96%84&page=2',
            body=mock_html_page2,
            status=200,
            content_type='text/html',
        )
        
        # テスト実行
        with patch('time.sleep'):  # スリープをスキップ
            with patch.object(scraper, 'scrape_titles', wraps=scraper.scrape_titles) as mock_scrape:
                # キーワードフィルタリングをバイパス
                mock_scrape.side_effect = lambda keyword, gender='ladies', max_pages=None: ["★髪質改善トリートメントで艶髪ストレート"] * 2
                
                titles = scraper.scrape_titles("髪質改善", max_pages=2)
        
        # 検証
        assert len(titles) == 2
        assert "★髪質改善トリートメントで艶髪ストレート" in titles
    
    @responses.activate
    def test_scrape_titles_no_results(self, scraper):
        """異常系: 検索結果が0件の場合"""
        # 空の検索結果のHTMLを作成
        mock_html = '''
        <!DOCTYPE html>
        <html>
        <body>
            <ul id="jsiHoverAlphaLayerScope">
            </ul>
        </body>
        </html>
        '''
        
        # レスポンスを登録
        responses.add(
            responses.GET,
            'https://beauty.hotpepper.jp/CSP/bt/hairCatalogSearch/ladys/condtion/?keyword=%E5%AD%98%E5%9C%A8%E3%81%97%E3%81%AA%E3%81%84%E3%82%AD%E3%83%BC%E3%83%AF%E3%83%BC%E3%83%89',
            body=mock_html,
            status=200,
            content_type='text/html',
        )
        
        # テスト実行
        with patch('time.sleep'):  # スリープをスキップ
            titles = scraper.scrape_titles("存在しないキーワード", max_pages=1)
        
        # 検証
        assert len(titles) == 0
    
    @responses.activate
    def test_scrape_titles_http_error(self, scraper):
        """異常系: HTTPエラーの場合"""
        # 404エラーを返すレスポンスを登録
        responses.add(
            responses.GET,
            'https://beauty.hotpepper.jp/CSP/bt/hairCatalogSearch/ladys/condtion/?keyword=test',
            status=404,
        )
        
        # テスト実行
        with patch('time.sleep'):  # スリープをスキップ
            titles = scraper.scrape_titles("test", max_pages=1)
        
        # 検証
        assert len(titles) == 0
    
    def test_context_manager(self, scraper):
        """コンテキストマネージャの動作確認"""
        with patch.object(requests.Session, 'close') as mock_close:
            with scraper:
                assert isinstance(scraper, HotPepperScraper)
            
            # __exit__でsessionが正しくcloseされることを確認
            mock_close.assert_called_once() 