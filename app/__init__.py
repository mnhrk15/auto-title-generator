from flask import Flask
from . import config
import logging
import os
from logging.handlers import RotatingFileHandler

def create_app():
    app = Flask(__name__)
    app.config.from_object(config.Config)
    
    # ロギングの設定
    setup_logging(app)
    
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
    logging.getLogger('selenium').addHandler(file_handler)
    
    app.logger.info('ロギングシステムが初期化されました')

app = create_app() 