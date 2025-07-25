import aiohttp
from urllib.parse import quote
from bs4 import BeautifulSoup
import time
import random
import logging
import os
import asyncio
import ssl
from typing import List
from . import config

# ロガーの設定
logger = logging.getLogger(__name__)

class HotPepperScraper:
    """aiohttpとBeautifulSoupを使用した非同期スクレイパー"""
    
    # セレクタ定数
    STYLE_TITLE_SELECTOR = "#jsiHoverAlphaLayerScope > li > div.mT5 > a > p > span"
    NEXT_PAGE_SELECTOR = "#searchList > div:nth-child(2) > div.pT5.pr.cFix > div > ul > li.pa.top0.right0.afterPage > a"
    
    def __init__(self):
        # 非同期セッションはコンテキストマネージャで管理するため
        # 初期化時にはセッションを作成しない
        self.session = None
        
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
        
        # 環境に応じたSSL設定
        # 開発環境ではSSL検証を無効に、本番環境では有効にする
        self.is_production = os.getenv('FLASK_ENV') == 'production'
        
        if not self.is_production:
            # 開発環境ではSSL検証を無効化
            logger.warning("開発環境のため、SSL証明書検証を無効化します。本番環境では有効にしてください。")
            # SSL検証を無効にするコンテキスト
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        else:
            # 本番環境ではデフォルトのSSL設定を使用
            self.ssl_context = True
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    # 下位互換性のために同期版のコンテキストマネージャも残す
    def __enter__(self):
        # 同期版から呼び出す場合の互換対応
        logger.warning("同期版のコンテキストマネージャが使用されました。非同期版の __aenter__ を使用することをお勧めします。")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.session = self.loop.run_until_complete(
            aiohttp.ClientSession(
                headers=self.headers,
                connector=aiohttp.TCPConnector(ssl=self.ssl_context)
            ).__aenter__()
        )
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 同期版から呼び出す場合の互換対応
        if self.session:
            self.loop.run_until_complete(self.session.close())
        if hasattr(self, 'loop') and self.loop:
            self.loop.close()
    
    async def scrape_titles_async(self, keyword: str, gender: str = 'ladies', max_pages: int = None) -> List[str]:
        """指定されたキーワードでヘアスタイルのタイトルを非同期で取得する"""
        if max_pages is None:
            max_pages = config.MAX_PAGES
            
        titles = []
        
        # 性別に応じたURLを選択
        base_url = config.MENS_URL if gender == 'mens' else config.LADIES_URL
        encoded_keyword = quote(keyword)
        
        logger.info(f"非同期スクレイピング開始: キーワード '{keyword}', 性別 '{gender}'")
        
        try:
            for page in range(1, max_pages + 1):
                try:
                    # ページURLの構築
                    url = f"{base_url}?keyword={encoded_keyword}"
                    if page > 1:
                        url += f"&pn={page}"
                    
                    logger.info(f"ページ {page} をスクレイピング中: {url}")
                    
                    # 非同期HTTPリクエスト
                    async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        # エラーチェック
                        response.raise_for_status()
                        
                        # レスポンスの詳細をログに記録
                        logger.debug(f"HTTPステータス: {response.status}, コンテンツタイプ: {response.headers.get('Content-Type')}")
                        
                        # テキストを非同期で取得
                        html_text = await response.text()
                        
                        # HTMLの解析
                        soup = BeautifulSoup(html_text, 'html.parser')
                        style_items = soup.select(self.STYLE_TITLE_SELECTOR)
                        
                        logger.info(f"スタイルアイテム数: {len(style_items)}")
                        
                        if len(style_items) == 0:
                            logger.warning(f"ページ {page}: スタイルアイテムが見つかりませんでした")
                            # HTMLの部分をログに記録して、セレクタがマッチしない理由を調査
                            logger.debug(f"HTML構造の一部: {soup.select('#jsiHoverAlphaLayerScope')}")
                            break
                        
                        # キーワードを含むタイトルをフィルタリング
                        page_titles = []
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
                        
                        # レート制限対策の待機（asyncioの非同期待機を使用）
                        await asyncio.sleep(random.uniform(
                            config.SCRAPING_DELAY_MIN,
                            config.SCRAPING_DELAY_MAX
                        ))
                            
                except aiohttp.ClientError as e:
                    logger.error(f"ページ {page} の取得中にエラーが発生: {str(e)}")
                    break
            
            # 重複を除去して元の順序を維持
            unique_titles = list(dict.fromkeys(titles))
            
            logger.info(f"スクレイピング完了: {len(titles)} 件のタイトルを取得後、重複を除き {len(unique_titles)} 件になりました")
            return unique_titles
            
        except Exception as e:
            logger.error(f"スクレイピング中に予期せぬエラーが発生: {str(e)}")
            raise
    
    # 下位互換性のために同期版も提供
    def scrape_titles(self, keyword: str, gender: str = 'ladies', max_pages: int = None) -> List[str]:
        """指定されたキーワードでヘアスタイルのタイトルを取得する (同期版ラッパー)"""
        logger.info("同期版 scrape_titles が呼び出されました - 内部で非同期処理を実行します")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if self.session is None:
                # 既存のセッションがない場合は一時的に作成
                async def _scrape_with_temp_session():
                    async with aiohttp.ClientSession(
                        headers=self.headers,
                        connector=aiohttp.TCPConnector(ssl=self.ssl_context)
                    ) as temp_session:
                        self.session = temp_session
                        result = await self.scrape_titles_async(keyword, gender, max_pages)
                        self.session = None
                        return result
                return loop.run_until_complete(_scrape_with_temp_session())
            else:
                # 既存のセッションがある場合はそれを使用
                return loop.run_until_complete(self.scrape_titles_async(keyword, gender, max_pages))
        finally:
            loop.close()