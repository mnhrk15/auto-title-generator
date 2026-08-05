import logging
from logging.handlers import RotatingFileHandler

from flask import Flask

from . import config
from .config import Settings
from .featured_keywords import EXTENSION_KEY, FeaturedKeywordsManager
from .main import main_bp

# 二重登録を検出するためのマーカー。同一プロセスで create_app() が複数回呼ばれても
# ログハンドラが積み上がらないようにする。
_LOG_HANDLER_NAME = 'auto-title-generator-file'
_LOG_STREAM_HANDLER_NAME = 'auto-title-generator-stream'


def create_app(settings: Settings | None = None) -> Flask:
    """Flask アプリケーションを生成する。

    Args:
        settings: 使用する設定。省略時はプロセス共有の設定（環境変数由来）を使う。
                  テストから環境変数をバイパスして設定を注入するために用意している。
    """
    app = Flask(__name__)

    settings = settings or config.get_settings()
    app.config.from_mapping(settings.flask_config())
    app.config['SETTINGS'] = settings

    setup_logging(app, settings)

    # 特集キーワードはワーカープロセスごとに一度だけ読み込む。
    # 以前は main.py のモジュールレベルで生成しており、import 時にファイル I/O が走り、
    # かつ相対パス解決だったため実行時の CWD に依存していた。
    app.extensions[EXTENSION_KEY] = FeaturedKeywordsManager(settings.featured_keywords_path)

    app.register_blueprint(main_bp)

    return app


def setup_logging(app: Flask, settings: Settings) -> None:
    """アプリケーション全体のロギング設定。

    ハンドラは root ロガーに付ける。これにより app.logger だけでなく、
    各モジュールの logging.getLogger(__name__) のログも同じ出力先へ流れる。
    冪等なので create_app() が複数回呼ばれてもハンドラは重複しない。

    出力先はファイルと標準エラーの2系統。Render はコンテナの stdout/stderr を収集するため、
    ストリーム側が無いとデプロイ後のログがダッシュボードに一切出なくなる
    （ファイルはコンテナの再起動で消えるので、ファイルだけでは運用ログにならない）。
    """
    root_logger = logging.getLogger()

    if any(getattr(h, 'name', None) == _LOG_HANDLER_NAME for h in root_logger.handlers):
        return

    settings.log_dir.mkdir(parents=True, exist_ok=True)

    # 開発環境ではDEBUG、本番環境ではINFO
    level = logging.DEBUG if app.debug else logging.INFO
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = RotatingFileHandler(
        settings.log_dir / 'app.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=10,
    )
    file_handler.name = _LOG_HANDLER_NAME
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.name = _LOG_STREAM_HANDLER_NAME
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    root_logger.addHandler(stream_handler)

    root_logger.setLevel(level)

    app.logger.info('ロギングシステムが初期化されました')
