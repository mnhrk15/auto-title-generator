"""アプリケーション設定。

環境に依存しない値はモジュール定数として置き、
環境変数に由来する値だけを ``Settings``（frozen dataclass）に隔離する。

``Settings`` は import 時ではなく ``get_settings()`` の初回呼び出し時に生成されるため、
テストから ``reset_settings()`` を挟むことで環境変数の差し替えが効く。
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

# --- スクレイピング対象 URL ---
LADIES_URL = 'https://beauty.hotpepper.jp/CSP/bt/hairCatalogSearch/ladys/condtion/'
MENS_URL = 'https://beauty.hotpepper.jp/CSP/bt/hairCatalogSearch/mens/condtion/'

# --- 性別 ---
GENDERS = ('ladies', 'mens')

# --- キーワード解析 ---
# 複合キーワードの区切りとして扱う文字（半角/全角スペース、カンマ、読点、スラッシュ、プラス）
KEYWORD_SEPARATORS = (' ', '　', ',', '、', '/', '＋', '+')

# --- Gemini モデル ---
DEFAULT_MODEL = 'gemini-3.1-flash-lite'
SUPPORTED_MODELS = ('gemini-3.1-flash-lite', 'gemini-3-flash-preview')
GEMINI_TEMPERATURE = 1.0  # Gemini 3 系は 1.0 未満にすると出力品質が落ちる
GEMINI_MAX_OUTPUT_TOKENS = 32768
# タイムアウトとリトライの予算:
#   gunicorn.conf.py の timeout=120 と、フロントエンドの AbortController(120秒) が上限。
#   これは「スクレイピング + 生成」を合わせたリクエスト全体に掛かる上限である点に注意。
#     生成: 40秒 × 2回 + 最大バックオフ4秒 ≒ 84秒
#     スクレイピング: MAX_PAGES × (1ページ10秒 + 待機最大3秒)
#   本番の MAX_PAGES=1 なら 13 + 84 ≒ 97秒で収まるが、既定の MAX_PAGES=3 では
#   39 + 84 ≒ 123秒となり 120秒を超え得るため、MAX_PAGES を増やす場合は
#   gunicorn の timeout とフロントエンドの AbortController も併せて見直すこと。
#   attempts=3 かつ 45秒 にすると生成だけで 138秒となりワーカーが先に殺されるため不可。
GEMINI_REQUEST_TIMEOUT_MS = 40_000
GEMINI_RETRY_ATTEMPTS = 2  # 初回 + リトライ1回
GEMINI_RETRY_INITIAL_DELAY = 1.0
GEMINI_RETRY_MAX_DELAY = 4.0

# --- テンプレート生成 ---
MAX_TEMPLATES = 20
CHAR_LIMITS = {
    'title': 30,
    'menu': 50,
    'comment': 120,
    'hashtag': 20,  # per word
}
# プロンプトの目標帯と生成後の検証で共有する値（片方だけ変えて不整合にならないようにする）
HASHTAG_MIN_COUNT = 7
# 各要素の目標文字数帯（上限は CHAR_LIMITS。目標帯は上限の少し手前を狙わせるための値）
TITLE_TARGET = (25, 28)
MENU_TARGET = (40, 47)
COMMENT_TARGET = (90, 115)

# --- 特集キーワードデータの検証上限 ---
FEATURED_NAME_MAX = 50
FEATURED_KEYWORD_MAX = 50
FEATURED_CONDITION_MAX = 500
FEATURED_FILE_MAX_BYTES = 1024 * 1024

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
SEASON_APPEND_THRESHOLD = 26  # この文字数未満のタイトルのみ付加対象
# 短尺タイトル枠: 付加後にちょうど上限文字数へ届くよう、付加する語の長さごとに目標帯を作る。
# 目標帯の上限は「上限文字数 - 区切り記号1文字 - キーワード長」で、そこから
# SHORT_TITLE_BAND_WIDTH 文字下までを許容幅とする（例: 春カラー → 23〜25文字）
SHORT_TITLE_BAND_WIDTH = 2
SHORT_TITLE_SLOTS_PER_CHOICE = 4  # チェック1つあたりの短尺枠数
SHORT_TITLE_SLOTS_MAX = 12  # 短尺枠の合計上限（MAX_TEMPLATES のうち）


def normalize_seasons(seasons: list[str] | None, gender: str) -> list[str]:
    """季節・カラー選択値を SEASON_COLOR_CHOICES の定義順に正規化する（未知値と重複を除去）。

    メンズでは季節カラー／ブリーチなしカラーを一切扱わないため常に空リストを返す。
    """
    if gender == 'mens' or not seasons:
        return []
    return [key for key in SEASON_COLOR_CHOICES if key in seasons]


_TRUE_VALUES = ('1', 'true', 'yes', 'on')
_FALSE_VALUES = ('0', 'false', 'no', 'off')


def _env_bool(name: str, default: bool) -> bool:
    """環境変数を真偽値として読む。

    解釈できない値では default を返す（既定値が安全側であるものに使うため、
    書きかけの空文字やタイポで黙って無効化されないようにする）。
    """
    raw = os.getenv(name)
    if raw is None:
        return default

    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False

    logger.warning(
        f'環境変数 {name} の値 "{raw}" を真偽値として解釈できません - 既定値 {default} を使用します'
    )
    return default


@dataclass(frozen=True)
class Settings:
    """環境変数に由来する設定値。"""

    gemini_api_key: str | None
    scraping_delay_min: float
    scraping_delay_max: float
    max_pages: int
    scraper_verify_ssl: bool
    secret_key: str
    debug: bool
    host: str
    port: int
    log_dir: Path
    featured_keywords_path: Path

    @classmethod
    def from_env(cls) -> 'Settings':
        load_dotenv()
        return cls(
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            scraping_delay_min=float(os.getenv('SCRAPING_DELAY_MIN', 1)),
            scraping_delay_max=float(os.getenv('SCRAPING_DELAY_MAX', 3)),
            max_pages=int(os.getenv('MAX_PAGES', 3)),
            # SSL 検証は既定で有効（fail-closed）。ローカル開発でのみ明示的に無効化する。
            scraper_verify_ssl=_env_bool('SCRAPER_VERIFY_SSL', True),
            secret_key=os.getenv('FLASK_SECRET_KEY', 'dev'),
            debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
            host=os.getenv('FLASK_HOST', '0.0.0.0'),  # Render でのデプロイ用
            port=int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000))),  # Render の PORT を優先
            log_dir=Path(os.getenv('LOG_DIR', PROJECT_ROOT / 'logs')),
            featured_keywords_path=Path(
                os.getenv('FEATURED_KEYWORDS_PATH', APP_DIR / 'data' / 'featured_keywords.json')
            ),
        )

    def flask_config(self) -> dict:
        """Flask の app.config に流し込む値。"""
        return {
            'SECRET_KEY': self.secret_key,
            'DEBUG': self.debug,
            'SERVER_NAME': None,
        }


_settings: Settings | None = None


def get_settings() -> Settings:
    """プロセス全体で共有する設定を返す（初回呼び出し時に環境変数から生成）。"""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """キャッシュ済みの設定を破棄する。テストで環境変数を差し替える際に使う。"""
    global _settings
    _settings = None
