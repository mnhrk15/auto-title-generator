import os
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
MAX_TEMPLATES = 15
CHAR_LIMITS = {
    'title': 30,
    'menu': 50,
    'comment': 120,
    'hashtag': 20  # per word
}

# Season Keywords for Prompt Engineering
SEASON_KEYWORDS = {
    "spring": ["春カラー", "スプリング"],
    "summer": ["夏カラー", "サマー"],
    "autumn": ["秋カラー", "オータム"],
    "winter": ["冬カラー", "ウィンター"],
    "all_year": ["定番", "いつでも人気", "ベーシック"],
    "graduation_entrance": ["卒業式", "入学式", "卒園式", "入園式", "新生活応援"],
    "rainy_season": ["梅雨", "湿気対策", "うねり解消", "縮毛矯正", "ストレートパーマ"],
    "year_end_new_year": ["年末年始", "クリスマス", "お正月", "冬休み", "カウントダウン", "成人式"]
}

# Flask Settings
class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')  # Renderでのデプロイ用に変更
    PORT = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))  # RenderのPORT環境変数を優先
    SERVER_NAME = None 