import os
import logging
import asyncio
import time # time モジュールをインポート
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify, current_app
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

app = Flask(__name__)
app.config['GEMINI_API_KEY'] = GEMINI_API_KEY

# ロギングの設定
setup_logging(app)

# エラーハンドラー
@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'サーバーエラー: {str(error)}')
    return jsonify({
        'success': False,
        'error': 'サーバー内部でエラーが発生しました。しばらく時間をおいて再度お試しください。',
        'status': 500
    }), 500

@app.errorhandler(404)
def not_found_error(error):
    app.logger.info(f'ページが見つかりません: {request.url}')
    return jsonify({
        'success': False,
        'error': 'リクエストされたページが見つかりません。',
        'status': 404
    }), 404

@app.errorhandler(400)
def bad_request_error(error):
    app.logger.warning(f'不正なリクエスト: {str(error)}')
    return jsonify({
        'success': False,
        'error': f'Invalid JSON: {str(error)}',
        'status': 400
    }), 400

@app.route('/favicon.ico')
def favicon():
    """faviconのルート"""
    return current_app.send_static_file('favicon.ico')

@app.route('/')
def index():
    """トップページのルート"""
    current_app.logger.info('トップページにアクセスがありました')
    return render_template('index.html')

# ヘルパー関数: 非同期処理の実行
def run_async_task(coro):
    """非同期コルーチンを同期的に実行するヘルパー関数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# スクレイピングと生成を非同期で行う関数
async def process_template_generation(keyword: str, gender: str, season: str = None) -> list:
    """スクレイピングとテンプレート生成を非同期で処理する"""
    current_app.logger.info(f'非同期処理開始: キーワード: "{keyword}", 性別: "{gender}", シーズン: "{season}"')
    process_start_time = time.perf_counter() # 全体処理開始時間
    
    # 非同期でスクレイピングを実行
    scraping_start_time = time.perf_counter()
    async with HotPepperScraper() as scraper:
        current_app.logger.info(f'スクレイピング開始: キーワード: "{keyword}", 性別: "{gender}"')
        titles = await scraper.scrape_titles_async(keyword, gender)
        scraping_end_time = time.perf_counter()
        current_app.logger.info(f'スクレイピング完了. 所要時間: {scraping_end_time - scraping_start_time:.2f}秒. {len(titles)}件のタイトルを取得')
    
    # スクレイピング結果をログに記録
    if titles:
        current_app.logger.info(f'スクレイピング結果のタイトル例 (最大10件):')
        for i, title in enumerate(titles[:10]):
            current_app.logger.info(f'  {i+1}: {title}')
        
        if len(titles) > 10:
            current_app.logger.info(f'  ... 他 {len(titles) - 10} 件')
    
    if not titles:
        current_app.logger.warning(f'キーワード "{keyword}" に一致するヘアスタイルが見つかりませんでした')
        return []
        
    # 非同期でテンプレート生成を実行
    generation_start_time = time.perf_counter()
    current_app.logger.info(f'テンプレート生成開始: キーワード: "{keyword}", タイトル数: {len(titles)}, シーズン: "{season}"')
    generator = TemplateGenerator()
    templates = await generator.generate_templates_async(titles, keyword, season)
    generation_end_time = time.perf_counter()
    current_app.logger.info(f'テンプレート生成完了. 所要時間: {generation_end_time - generation_start_time:.2f}秒. {len(templates)}件のテンプレートを生成')
    
    # 生成されたテンプレートをログに記録
    for i, template in enumerate(templates):
        current_app.logger.info(f'生成テンプレート {i+1}:')
        current_app.logger.info(f'  タイトル: {template.get("title", "不明")}')
        current_app.logger.info(f'  メニュー: {template.get("menu", "不明")}')
        current_app.logger.info(f'  ハッシュタグ: {template.get("hashtag", "不明")}')
        
        # キーワードチェック
        if keyword.lower() in template.get("title", "").lower():
            current_app.logger.info(f'  ✅ タイトルにキーワード "{keyword}" が含まれています')
        else:
            current_app.logger.warning(f'  ❌ タイトルにキーワード "{keyword}" が含まれていません: "{template.get("title", "")}"')
    
    process_end_time = time.perf_counter() # 全体処理終了時間
    current_app.logger.info(f'非同期処理完了. 全体所要時間: {process_end_time - process_start_time:.2f}秒')
    return templates

@app.route('/api/generate', methods=['POST'])
def generate():
    """テンプレート生成のAPIエンドポイント"""
    try:
        # 不正なJSONリクエストの場合は400エラーを返す
        if request.is_json is False and request.data:
            current_app.logger.warning('不正なJSONリクエストを受信しました')
            return jsonify({
                'success': False,
                'error': 'Invalid JSON: The request payload is not valid JSON',
                'status': 400
            }), 400
            
        data = request.get_json()
        if not data:
            current_app.logger.warning('リクエストデータがありません')
            return jsonify({
                'success': False,
                'error': 'リクエストデータが不正です。キーワードを入力してください。',
                'status': 400
            }), 400
        
        keyword = data.get('keyword')
        gender = data.get('gender', 'ladies')
        season = data.get('season') # 'none' や空文字の場合もありうる
        num_templates = int(data.get('num_templates', 5)) # この変数は現在 process_template_generation で使われていないが、将来のために残す
        
        current_app.logger.info(f'テンプレート生成リクエスト - キーワード: "{keyword}", 性別: "{gender}", シーズン: "{season}", テンプレート数: {num_templates}')
        
        if not keyword:
            return jsonify({
                'success': False,
                'error': 'キーワードを入力してください。',
                'status': 400
            }), 400
            
        if gender not in ['ladies', 'mens']:
            return jsonify({
                'success': False,
                'error': '無効な性別が指定されました。',
                'status': 400
            }), 400
            
        # 非同期処理を同期的に実行
        templates = run_async_task(process_template_generation(keyword, gender, season))
        
        if not templates:
            return jsonify({
                'success': False,
                'error': '一致するヘアスタイルが見つかりませんでした。別のキーワードをお試しください。',
                'status': 404
            }), 404
        
        return jsonify({
            'success': True,
            'templates': templates,
            'status': 200
        })
        
    except BadRequest as e:
        current_app.logger.warning(f'不正なJSONリクエスト: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'Invalid JSON: {str(e)}',
            'status': 400
        }), 400
        
    except ValueError as e:
        current_app.logger.warning(f'不正なリクエスト: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 400
        }), 400
        
    except Exception as e:
        current_app.logger.error(f'テンプレート生成中にエラー: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'テンプレート生成中にエラーが発生しました。',
            'status': 500
        }), 500

if __name__ == '__main__':
    app.run(debug=True)