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
MAX_TEMPLATES = 5
CHAR_LIMITS = {
    'title': 30,
    'menu': 50,
    'comment': 120,
    'hashtag': 20  # per word
}

# Flask Settings
class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')  # Renderでのデプロイ用に変更
    PORT = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))  # RenderのPORT環境変数を優先
    SERVER_NAME = None 