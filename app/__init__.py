from flask import Flask
from . import config
import logging
import os
from logging.handlers import RotatingFileHandler
from .main import main_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(config.Config)
    
    # ロギングの設定
    setup_logging(app)
    
    # Blueprintの登録
    app.register_blueprint(main_bp)
    
    return app

def setup_logging(app):
    """アプリケーション全体のロギング設定"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=10
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # 開発環境ではDEBUG、本番環境ではINFO
    if app.debug:
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)
    
    app.logger.addHandler(file_handler)
    
    # 他のモジュールのロガー設定
    logging.getLogger('werkzeug').addHandler(file_handler)
    
    app.logger.info('ロギングシステムが初期化されました')

app = create_app()

# ルートの登録 (Blueprint に移管したため不要)
# from . import main # create_app() の中で main_bp をインポートしているので不要

# Expose routes (Blueprint に移管したため不要)
# app.add_url_rule('/', 'index', main.index)
# app.add_url_rule('/favicon.ico', 'favicon', main.favicon) 