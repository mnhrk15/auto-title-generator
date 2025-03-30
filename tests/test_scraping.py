import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.scraping import HotPepperScraper
from unittest.mock import patch, MagicMock

class TestHotPepperScraper:
    @pytest.fixture
    def mock_driver(self):
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            driver = MagicMock()
            mock_chrome.return_value = driver
            yield driver
            
    @pytest.fixture
    def mock_service(self):
        with patch('selenium.webdriver.chrome.service.Service') as mock_service:
            yield mock_service
            
    @pytest.fixture
    def scraper(self):
        return HotPepperScraper()
        
    def test_setup_chrome_options(self, scraper):
        """Chromeオプションが正しく設定されているかテスト"""
        options = scraper._setup_chrome_options()
        
        # ヘッドレスモードと必要なオプションが設定されているか確認
        assert '--headless' in options.arguments
        assert '--no-sandbox' in options.arguments
        assert '--disable-dev-shm-usage' in options.arguments
        
    def test_scrape_titles_success(self, scraper, mock_driver, mock_service):
        """正常系: タイトルの取得が成功するケース"""
        # モックのHTMLコンテンツを設定
        mock_html = '''
        <div class="style-list">
            <span class="photoCaption">★小顔イメチェン似合わせ美髪ワンカールレイヤーカット</span>
            <span class="photoCaption">★髪質改善トリートメントで艶髪ストレート</span>
            <span class="photoCaption">★大人可愛いボブスタイル</span>
        </div>
        '''
        
        # 検索ボックスのモック
        mock_search_box = MagicMock()
        mock_driver.find_element.return_value = mock_search_box
        
        # WebDriverWaitのモック
        mock_wait = MagicMock()
        mock_wait.until.return_value = mock_search_box
        
        with patch('selenium.webdriver.support.ui.WebDriverWait', return_value=mock_wait):
            # page_sourceプロパティをモック
            type(mock_driver).page_source = mock_html
            
            # 次へボタンが無効な状態をモック（1ページ目で終了）
            mock_next_button = MagicMock()
            mock_next_button.is_enabled.return_value = False
            mock_driver.find_element.return_value = mock_next_button
            
            # スクレイピング実行
            scraper.driver = mock_driver
            titles = scraper.scrape_titles("髪質改善")
            
            # 検証
            assert len(titles) == 1
            assert titles[0] == "★髪質改善トリートメントで艶髪ストレート"
            
    def test_scrape_titles_no_results(self, scraper, mock_driver, mock_service):
        """異常系: 検索結果が0件の場合"""
        # 空の検索結果をモック
        mock_html = '<div class="style-list"></div>'
        
        # 検索ボックスのモック
        mock_search_box = MagicMock()
        mock_driver.find_element.return_value = mock_search_box
        
        # WebDriverWaitのモック
        mock_wait = MagicMock()
        mock_wait.until.return_value = mock_search_box
        
        with patch('selenium.webdriver.support.ui.WebDriverWait', return_value=mock_wait):
            type(mock_driver).page_source = mock_html
            
            scraper.driver = mock_driver
            titles = scraper.scrape_titles("存在しないキーワード")
            
            assert len(titles) == 0
            
    def test_scrape_titles_timeout(self, scraper, mock_driver, mock_service):
        """異常系: ページ読み込みタイムアウトの場合"""
        from selenium.common.exceptions import TimeoutException
        
        # WebDriverWaitのモックでTimeoutExceptionを発生させる
        mock_wait = MagicMock()
        mock_wait.until.side_effect = TimeoutException()
        
        with patch('selenium.webdriver.support.ui.WebDriverWait', return_value=mock_wait):
            scraper.driver = mock_driver
            type(mock_driver).page_source = '<div></div>'
            titles = scraper.scrape_titles("キーワード")
            
            assert len(titles) == 0
            
    def test_context_manager(self, scraper):
        """コンテキストマネージャの動作確認"""
        mock_driver = MagicMock()
        
        with patch('selenium.webdriver.Chrome', return_value=mock_driver):
            with scraper as s:
                assert isinstance(s, HotPepperScraper)
                s.driver = mock_driver
            
            # __exit__でdriverが正しくquitされることを確認
            mock_driver.quit.assert_called_once() 