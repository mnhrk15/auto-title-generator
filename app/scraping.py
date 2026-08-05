import asyncio
import logging
import random
import ssl
from urllib.parse import quote

import aiohttp
import certifi
from bs4 import BeautifulSoup

from . import config
from .errors import ScrapingError

# ロガーの設定
logger = logging.getLogger(__name__)


class HotPepperScraper:
    """aiohttpとBeautifulSoupを使用した非同期スクレイパー"""

    # セレクタ定数
    STYLE_TITLE_SELECTOR = "#jsiHoverAlphaLayerScope > li > div.mT5 > a > p > span"
    NEXT_PAGE_SELECTOR = "#searchList > div:nth-child(2) > div.pT5.pr.cFix > div > ul > li.pa.top0.right0.afterPage > a"

    def __init__(self, settings: config.Settings | None = None):
        self.settings = settings or config.get_settings()

        # 非同期セッションはコンテキストマネージャで管理するため
        # 初期化時にはセッションを作成しない
        self.session = None

        # ヘッダー設定
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Sec-Ch-Ua': '"Chromium";v="134", "Not(A:Brand";v="24", "Google Chrome";v="134"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Upgrade-Insecure-Requests': '1',
        }

        # SSL 検証は既定で有効。SCRAPER_VERIFY_SSL=false を明示した場合のみ無効化する。
        # CA は certifi のバンドルを使う。OS の証明書ストアに依存すると、
        # macOS の python.org 版のように「unable to get local issuer certificate」で
        # 検証が通らない環境が出てくるため。
        if self.settings.scraper_verify_ssl:
            self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        else:
            logger.warning(
                "SCRAPER_VERIFY_SSL=false のため SSL 証明書検証を無効化します。"
                "この設定は開発環境でのみ使用してください。"
            )
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self.headers, connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def scrape_titles_async(
        self, keyword: str, gender: str = 'ladies', max_pages: int = None
    ) -> list[str]:
        """指定されたキーワードでヘアスタイルのタイトルを非同期で取得する"""
        if max_pages is None:
            max_pages = self.settings.max_pages

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
                    async with self.session.get(
                        url, timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        # エラーチェック
                        response.raise_for_status()

                        # レスポンスの詳細をログに記録
                        logger.debug(
                            f"HTTPステータス: {response.status}, コンテンツタイプ: {response.headers.get('Content-Type')}"
                        )

                        # テキストを非同期で取得
                        html_text = await response.text()

                        # HTMLの解析
                        soup = BeautifulSoup(html_text, 'html.parser')
                        style_items = soup.select(self.STYLE_TITLE_SELECTOR)

                        logger.info(f"スタイルアイテム数: {len(style_items)}")

                        if len(style_items) == 0:
                            logger.warning(f"ページ {page}: スタイルアイテムが見つかりませんでした")
                            # HTMLの部分をログに記録して、セレクタがマッチしない理由を調査
                            logger.debug(
                                f"HTML構造の一部: {soup.select('#jsiHoverAlphaLayerScope')}"
                            )
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
                            logger.info(f"タイトル {i + 1}: {title}")

                        # 次のページの有無をチェック
                        next_button = soup.select_one(self.NEXT_PAGE_SELECTOR)
                        if not next_button:
                            logger.info(
                                "次のページボタンが見つかりません。スクレイピングを終了します"
                            )
                            break

                        # レート制限対策の待機（asyncioの非同期待機を使用）
                        await asyncio.sleep(
                            random.uniform(
                                self.settings.scraping_delay_min, self.settings.scraping_delay_max
                            )
                        )

                # ClientTimeout(total=...) の超過は asyncio.TimeoutError（= 組み込みの
                # TimeoutError）で、aiohttp.ClientError のサブクラスではない。
                # 「サイトが遅い」は最も起きやすい失敗なので、必ず両方を捕捉する。
                except (TimeoutError, aiohttp.ClientError) as e:
                    # 1ページ目で失敗した場合は取得結果ゼロ件と区別できないため、
                    # 「該当なし」に化けないようエラーとして送出する。
                    # 2ページ目以降は既に有効なデータがあるので、取得済み分で続行する。
                    if page == 1:
                        logger.error(f"1ページ目の取得に失敗しました: {str(e)}")
                        raise ScrapingError() from e

                    logger.warning(
                        f"ページ {page} の取得中にエラーが発生: {str(e)} "
                        f"- 取得済みの {len(titles)} 件で続行します"
                    )
                    break

            # 重複を除去して元の順序を維持
            unique_titles = list(dict.fromkeys(titles))

            logger.info(
                f"スクレイピング完了: {len(titles)} 件のタイトルを取得後、重複を除き {len(unique_titles)} 件になりました"
            )
            return unique_titles

        except ScrapingError:
            # 既にログ済みで、ユーザー向けメッセージも確定しているのでそのまま送出する
            raise

        except Exception as e:
            logger.error(f"スクレイピング中に予期せぬエラーが発生: {str(e)}")
            raise
