import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Settings
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Scraping Settings
SCRAPING_DELAY_MIN = int(os.getenv('SCRAPING_DELAY_MIN', 1))
SCRAPING_DELAY_MAX = int(os.getenv('SCRAPING_DELAY_MAX', 3))
MAX_PAGES = int(os.getenv('MAX_PAGES', 3))

# Base URLs for HotPepper Beauty
LADIES_URL = 'https://beauty.hotpepper.jp/CSP/bt/hairCatalogSearch/ladys/condtion/'
MENS_URL = 'https://beauty.hotpepper.jp/CSP/bt/hairCatalogSearch/mens/condtion/'
BASE_URL = LADIES_URL  # デフォルトはレディース

# Template Generation Settings
MAX_TEMPLATES = 20
CHAR_LIMITS = {
    'title': 30,
    'menu': 50,
    'comment': 120,
    'hashtag': 20  # per word
}

# 季節・カラー付加キーワード（レディースのみ。UIのチェックボックスで複数選択できる）
# キーは index.html の input[name="season"] の value と一対一で対応する
SEASON_COLOR_CHOICES = {
    "spring": "春カラー",
    "summer": "夏カラー",
    "autumn": "秋カラー",
    "winter": "冬カラー",
    "bleach_free": "ブリーチなしカラー",
}
# 付加時の区切り記号。タイトルが SEASON_APPEND_DELIMITERS の記号を使っていればそれに合わせ、
# 使っていなければ SEASON_APPEND_SEPARATORS をこの順にローテーションする
SEASON_APPEND_SEPARATORS = ("◎", "/", "×")
SEASON_APPEND_DELIMITERS = ("/", "×")
SEASON_APPEND_THRESHOLD = 26       # この文字数未満のタイトルのみ付加対象
# 短尺タイトル枠: 付加後にちょうど上限文字数へ届くよう、付加する語の長さごとに目標帯を作る。
# 目標帯の上限は「上限文字数 - 区切り記号1文字 - キーワード長」で、そこから
# SHORT_TITLE_BAND_WIDTH 文字下までを許容幅とする（例: 春カラー → 23〜25文字）
SHORT_TITLE_BAND_WIDTH = 2
SHORT_TITLE_SLOTS_PER_CHOICE = 4   # チェック1つあたりの短尺枠数
SHORT_TITLE_SLOTS_MAX = 12         # 短尺枠の合計上限（MAX_TEMPLATES のうち）

# Maintenance Notice
JST = ZoneInfo('Asia/Tokyo')

# 臨時システムメンテナンス告知（'end' を過ぎると自動的に非表示になる。終了後はこの定数と関連コードを削除する）
MAINTENANCE_NOTICE = {
    'end': datetime(2026, 7, 21, 8, 0, tzinfo=JST),
    'message': 'HOT PEPPER Beauty／SALON BOARD の臨時システムメンテナンスのため、'
               '7月21日(火) 1:00〜8:00頃は本アプリのタイトル生成をご利用いただけません。',
}

# Flask Settings
class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')  # Renderでのデプロイ用に変更
    PORT = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))  # RenderのPORT環境変数を優先
    SERVER_NAME = None 