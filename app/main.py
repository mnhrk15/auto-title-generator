import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import BadRequest
from .scraping import HotPepperScraper
from .generator import TemplateGenerator
from .config import GEMINI_API_KEY

# ロガーの設定
def setup_logging(app):
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

app = Flask(__name__)
app.config['GEMINI_API_KEY'] = GEMINI_API_KEY

# ロギングの設定
setup_logging(app)

# エラーハンドラー
@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'サーバーエラー: {str(error)}')
    return jsonify({
        'error': 'サーバー内部でエラーが発生しました。しばらく時間をおいて再度お試しください。',
        'status': 500
    }), 500

@app.errorhandler(404)
def not_found_error(error):
    app.logger.info(f'ページが見つかりません: {request.url}')
    return jsonify({
        'error': 'リクエストされたページが見つかりません。',
        'status': 404
    }), 404

# faviconのルート
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.route('/')
def index():
    app.logger.info('トップページにアクセスがありました')
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        keyword = data.get('keyword')
        gender = data.get('gender', 'ladies')
        num_templates = int(data.get('num_templates', 5))
        
        app.logger.info(f'テンプレート生成リクエスト - キーワード: {keyword}, 性別: {gender}, テンプレート数: {num_templates}')
        
        if not keyword:
            return jsonify({
                'error': 'キーワードは必須です。',
                'status': 400
            }), 400
            
        if gender not in ['ladies', 'mens']:
            return jsonify({
                'error': '無効な性別が指定されました。',
                'status': 400
            }), 400
            
        with HotPepperScraper() as scraper:
            titles = scraper.scrape_titles(keyword, gender)
            
        if not titles:
            return jsonify({
                'error': 'スタイルが見つかりませんでした。別のキーワードをお試しください。',
                'status': 404
            }), 404
            
        generator = TemplateGenerator(GEMINI_API_KEY)
        templates = generator.generate_templates(titles, num_templates)
        
        app.logger.info(f'テンプレート生成成功 - {len(templates)}件のテンプレートを生成')
        
        return jsonify({
            'templates': templates,
            'status': 200
        })
        
    except ValueError as e:
        app.logger.warning(f'不正なリクエスト: {str(e)}')
        return jsonify({
            'error': str(e),
            'status': 400
        }), 400
        
    except Exception as e:
        app.logger.error(f'テンプレート生成中にエラー: {str(e)}')
        return jsonify({
            'error': 'テンプレート生成中にエラーが発生しました。',
            'status': 500
        }), 500

if __name__ == '__main__':
    app.run(debug=True) 