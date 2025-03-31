import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
import time
import random
import logging
import os
from typing import List
from . import config

# ロガーの設定
logger = logging.getLogger(__name__)

class HotPepperScraper:
    """requestsとBeautifulSoupを使用したスクレイパー"""
    
    # セレクタ定数
    STYLE_TITLE_SELECTOR = "#jsiHoverAlphaLayerScope > li > div.mT5 > a > p > span"
    NEXT_PAGE_SELECTOR = "#searchList > div:nth-child(2) > div.pT5.pr.cFix > div > ul > li.pa.top0.right0.afterPage > a"
    
    def __init__(self):
        # セッションの初期化
        self.session = requests.Session()
        
        # ヘッダー設定
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session.headers.update(self.headers)
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    def scrape_titles(self, keyword: str, gender: str = 'ladies', max_pages: int = None) -> List[str]:
        """指定されたキーワードでヘアスタイルのタイトルを取得する"""
        if max_pages is None:
            max_pages = config.MAX_PAGES
            
        titles = []
        
        # 性別に応じたURLを選択
        base_url = config.MENS_URL if gender == 'mens' else config.LADIES_URL
        encoded_keyword = quote(keyword)
        
        logger.info(f"スクレイピング開始: キーワード '{keyword}', 性別 '{gender}'")
        
        try:
            for page in range(1, max_pages + 1):
                try:
                    # ページURLの構築
                    url = f"{base_url}?keyword={encoded_keyword}"
                    if page > 1:
                        url += f"&page={page}"
                    
                    logger.info(f"ページ {page} をスクレイピング中: {url}")
                    
                    # HTTPリクエスト
                    response = self.session.get(url, timeout=10)
                    
                    # エラーチェック
                    response.raise_for_status()
                    
                    # レスポンスの詳細をログに記録
                    logger.debug(f"HTTPステータス: {response.status_code}, コンテンツタイプ: {response.headers.get('Content-Type')}")
                    
                    # HTMLの解析
                    soup = BeautifulSoup(response.text, 'html.parser')
                    style_items = soup.select(self.STYLE_TITLE_SELECTOR)
                    
                    logger.info(f"スタイルアイテム数: {len(style_items)}")
                    
                    if len(style_items) == 0:
                        logger.warning(f"ページ {page}: スタイルアイテムが見つかりませんでした")
                        # HTMLの部分をログに記録して、セレクタがマッチしない理由を調査
                        logger.debug(f"HTML構造の一部: {soup.select('#jsiHoverAlphaLayerScope')}")
                        break
                    
                    # キーワードを含むタイトルをフィルタリング
                    page_titles = []
                    filtered_count = 0
                    for item in style_items:
                        title_text = item.get_text(strip=True)
                        logger.debug(f"見つかったタイトル: {title_text}")
                        page_titles.append(title_text)
                    
                    titles.extend(page_titles)
                    logger.info(f"ページ {page}: {len(page_titles)} 件のタイトルを取得")
                    
                    # すべてのタイトルを記録
                    for i, title in enumerate(page_titles):
                        logger.info(f"タイトル {i+1}: {title}")
                    
                    # 次のページの有無をチェック
                    next_button = soup.select_one(self.NEXT_PAGE_SELECTOR)
                    if not next_button:
                        logger.info("次のページボタンが見つかりません。スクレイピングを終了します")
                        break
                    
                    # レート制限対策の待機
                    time.sleep(random.uniform(
                        config.SCRAPING_DELAY_MIN,
                        config.SCRAPING_DELAY_MAX
                    ))
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"ページ {page} の取得中にエラーが発生: {str(e)}")
                    break
            
            logger.info(f"スクレイピング完了: {len(titles)} 件のタイトルを取得しました")
            return titles
            
        except Exception as e:
            logger.error(f"スクレイピング中に予期せぬエラーが発生: {str(e)}")
            raise 