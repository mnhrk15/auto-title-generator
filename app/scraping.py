from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import random
import logging
import platform
import os
from typing import List
from . import config

# ロガーの設定
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

def setup_chromedriver():
    """ChromeDriverのセットアップを行う"""
    try:
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            # Apple Silicon用の設定
            service = ChromeService(ChromeDriverManager(os_type="mac-arm64").install())
        else:
            service = ChromeService(ChromeDriverManager().install())
        return service
    except Exception as e:
        logging.error(f"ChromeDriver設定エラー: {str(e)}")
        raise

def create_driver(service, options):
    """WebDriverの作成を行う（リトライ機能付き）"""
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            retry_count += 1
            logging.warning(f"ドライバー作成リトライ {retry_count}/{max_retries}: {str(e)}")
            time.sleep(1)
    raise Exception("ドライバーの作成に失敗しました")

class HotPepperScraper:
    # セレクタ定数
    SEARCH_BOX_SELECTOR = "#keyword > div > div.mT15 > p.cFix.kwInputWrapper"
    SEARCH_BUTTON_SELECTOR = "#keyword > div > div.mT15 > p.mT10 > input"
    STYLE_LIST_SELECTOR = "#jsiHoverAlphaLayerScope"
    STYLE_TITLE_SELECTOR = "#jsiHoverAlphaLayerScope > li > div.mT5 > a > p > span"
    NEXT_PAGE_SELECTOR = "#searchList > div:nth-child(2) > div.pT5.pr.cFix > div > ul > li.pa.top0.right0.afterPage > a"
    
    def __init__(self):
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        
        # User-Agentの設定
        if platform.system() == "Darwin":
            self.options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')
        elif platform.system() == "Windows":
            self.options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')
        else:
            self.options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')
        
    def __enter__(self):
        try:
            service = setup_chromedriver()
            self.driver = create_driver(service, self.options)
            return self
        except Exception as e:
            logging.error(f"スクレイパーの初期化に失敗: {str(e)}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except Exception as e:
                logging.warning(f"ドライバーのクリーンアップ中にエラー: {str(e)}")

    def scrape_titles(self, keyword: str, gender: str = 'ladies', max_pages: int = None) -> List[str]:
        if max_pages is None:
            max_pages = config.MAX_PAGES
            
        try:
            # WebDriver検出の回避
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            # ヘッダーの設定
            self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                'headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
                    'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"macOS"',
                    'Upgrade-Insecure-Requests': '1'
                }
            })
            
            titles = []
            
            # 性別に応じたURLを選択
            base_url = config.MENS_URL if gender == 'mens' else config.LADIES_URL
            
            # メインページにアクセス
            self.driver.get(base_url)
            
            # 人間らしい待機時間
            time.sleep(random.uniform(2, 4))
            
            try:
                # 検索ボックスの親要素を待機
                search_box_parent = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.SEARCH_BOX_SELECTOR))
                )
                search_input = search_box_parent.find_element(By.TAG_NAME, "input")
                
                # 人間らしい入力をシミュレート
                for char in keyword:
                    search_input.send_keys(char)
                    time.sleep(random.uniform(0.1, 0.3))
                
            except Exception as e:
                logging.error(f"検索ボックス操作中にエラーが発生: {str(e)}")
                raise
            
            # 検索ボタンをクリック
            try:
                search_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.SEARCH_BUTTON_SELECTOR))
                )
                time.sleep(random.uniform(0.5, 1.0))
                search_button.click()
                
            except Exception as e:
                logging.error(f"検索ボタンクリック中にエラーが発生: {str(e)}")
                raise
            
            for page in range(max_pages):
                try:
                    # ページの読み込みを待機
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, self.STYLE_LIST_SELECTOR))
                    )
                    
                    # スクロールを人間らしく実行
                    self.scroll_page_smoothly()
                    
                    # タイトルの取得
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    style_items = soup.select(self.STYLE_TITLE_SELECTOR)
                    
                    if len(style_items) == 0:
                        logging.warning(f"ページ {page+1}: スタイルアイテムが見つかりませんでした")
                        pass
                    
                    # キーワードを含むタイトルをフィルタリング
                    page_titles = []
                    for item in style_items:
                        title_text = item.get_text(strip=True)
                        if keyword.lower() in title_text.lower():
                            page_titles.append(title_text)
                            
                    titles.extend(page_titles)
                    logging.info(f"ページ {page+1}: {len(page_titles)} 件のタイトルを取得")
                    
                    # 次のページへ
                    if page < max_pages - 1:
                        try:
                            next_button = self.driver.find_element(By.CSS_SELECTOR, self.NEXT_PAGE_SELECTOR)
                            if not next_button.is_enabled():
                                logging.info("次のページボタンが無効です。スクレイピングを終了します")
                                break
                                
                            # スクロールして次のページボタンを表示
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                            time.sleep(random.uniform(0.5, 1.0))
                            next_button.click()
                            
                            # ランダムな待機時間
                            time.sleep(random.uniform(
                                config.SCRAPING_DELAY_MIN + 1,
                                config.SCRAPING_DELAY_MAX + 1
                            ))
                        except NoSuchElementException:
                            logging.info("次のページボタンが見つかりません。スクレイピングを終了します")
                            break
                        
                except (TimeoutException, NoSuchElementException) as e:
                    logging.warning(f"ページ {page+1} の処理中にエラーが発生: {str(e)}")
                    break
                    
            logging.info(f"スクレイピング完了: {len(titles)} 件のタイトルを取得しました")
            return titles
            
        except Exception as e:
            logging.error(f"スクレイピング中に予期せぬエラーが発生: {str(e)}")
            raise

    def scroll_page_smoothly(self):
        """ページを人間らしくスクロール"""
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        current_height = 0
        step = 300  # 一回のスクロール量
        
        while current_height < total_height:
            current_height += step
            self.driver.execute_script(f"window.scrollTo(0, {current_height});")
            time.sleep(random.uniform(0.1, 0.3))
                
    def scrape_titles_old(self, keyword, gender='ladies', max_pages=3):
        """指定されたキーワードでヘアスタイルのタイトルを取得する"""
        titles = []
        base_url = f"https://beauty.hotpepper.jp/catalog/{gender}/hair/style/"
        
        try:
            for page in range(1, max_pages + 1):
                try:
                    url = f"{base_url}?keyword={keyword}&page={page}"
                    self.driver.get(url)
                    
                    # ページ読み込み待機
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#jsiHoverAlphaLayerScope"))
                    )
                    
                    # タイトル要素を取得
                    title_elements = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "#jsiHoverAlphaLayerScope > li > div.mT5 > a > p > span"
                    )
                    
                    # タイトルを抽出
                    page_titles = [element.text for element in title_elements if element.text.strip()]
                    titles.extend(page_titles)
                    
                    logger.info(f"ページ {page}: {len(page_titles)} 件のタイトルを取得")
                    
                    # 次のページが存在するか確認
                    next_button = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "#searchList > div:nth-child(2) > div.pT5.pr.cFix > div > ul > li.pa.top0.right0.afterPage > a"
                    )
                    if not next_button:
                        break
                    
                    # ウェイト
                    time.sleep(random.uniform(config.SCRAPING_DELAY_MIN, config.SCRAPING_DELAY_MAX))
                    
                except TimeoutException:
                    logger.warning(f"ページ {page} の読み込みタイムアウト")
                    break
                except WebDriverException as e:
                    logger.error(f"ページ {page} のスクレイピング中にエラー: {str(e)}")
                    break
            
            logger.info(f"スクレイピング完了: {len(titles)} 件のタイトルを取得しました")
            return titles
            
        except Exception as e:
            logger.error(f"スクレイピング処理全体でエラー: {str(e)}")
            raise 