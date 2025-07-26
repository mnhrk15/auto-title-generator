import os
import logging
# import asyncio # Removed as run_async_task is deleted
from logging.handlers import RotatingFileHandler
from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.exceptions import BadRequest
from .scraping import HotPepperScraper
from .generator import TemplateGenerator
from .config import GEMINI_API_KEY

# Blueprintの作成
main_bp = Blueprint('main', __name__)

# ロガーの設定
# def setup_logging(app): # app/__init__.py で実行されるため不要
#     if not os.path.exists('logs'):
#         os.makedirs('logs')
#     
#     file_handler = RotatingFileHandler(
#         'logs/app.log',
#         maxBytes=1024 * 1024,  # 1MB
#         backupCount=10
#     )
#     
#     formatter = logging.Formatter(
#         '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     )
#     file_handler.setFormatter(formatter)
#     
#     # 開発環境ではDEBUG、本番環境ではINFO
#     if app.debug:
#         file_handler.setLevel(logging.DEBUG)
#     else:
#         file_handler.setLevel(logging.INFO)
#     
#     app.logger.addHandler(file_handler)
#     
#     # 他のモジュールのロガー設定
#     logging.getLogger('werkzeug').addHandler(file_handler)

# app = Flask(__name__) # ここで app を再定義しない
# app.config['GEMINI_API_KEY'] = GEMINI_API_KEY # config は app/__init__.py で読み込まれる

# ロギングの設定
# setup_logging(app) # app/__init__.py で実行されるため不要

# エラーハンドラー
@main_bp.app_errorhandler(500)
def internal_error(error):
    current_app.logger.error(f'サーバーエラー: {str(error)}')
    return jsonify({
        'success': False,
        'error': {
            'message': 'サーバー内部でエラーが発生しました。しばらく時間をおいて再度お試しください。',
            'code': 'INTERNAL_SERVER_ERROR'
        },
        'status': 500
    }), 500

@main_bp.app_errorhandler(404)
def not_found_error(error):
    current_app.logger.info(f'ページが見つかりません: {request.url}')
    return jsonify({
        'success': False,
        'error': {
            'message': 'リクエストされたページが見つかりません。',
            'code': 'NOT_FOUND'
        },
        'status': 404
    }), 404

@main_bp.app_errorhandler(400)
def bad_request_error(error):
    # BadRequest 例外から元のメッセージを取得しようと試みる
    # werkzeug.exceptions.BadRequest は description 属性にメッセージを持つ
    message = str(error)
    if hasattr(error, 'description') and error.description:
        message = error.description
        
    current_app.logger.warning(f'不正なリクエスト: {message}')
    return jsonify({
        'success': False,
        'error': {
            'message': f'不正なリクエストです: {message}',
            'code': 'BAD_REQUEST'
        },
        'status': 400
    }), 400

@main_bp.route('/favicon.ico')
def favicon():
    """faviconのルート"""
    return current_app.send_static_file('favicon.ico')

@main_bp.route('/')
def index():
    """トップページのルート"""
    current_app.logger.info('トップページにアクセスがありました')
    return render_template('index.html')

# スクレイピングと生成を非同期で行う関数
async def process_template_generation(keyword: str, gender: str, season: str = None, model: str = 'gemini-2.5-flash') -> list:
    """スクレイピングとテンプレート生成を非同期で処理する"""
    current_app.logger.info(f'非同期処理開始: キーワード: "{keyword}", 性別: "{gender}", シーズン: "{season}", モデル: "{model}"')
    
    # 非同期でスクレイピングを実行
    async with HotPepperScraper() as scraper:
        current_app.logger.info(f'スクレイピング開始: キーワード: "{keyword}", 性別: "{gender}"')
        titles = await scraper.scrape_titles_async(keyword, gender)
        current_app.logger.info(f'スクレイピング結果: {len(titles)} 件のタイトルを取得')
    
    # スクレイピング結果をログに記録
    if titles:
        current_app.logger.debug(f"スクレイピングで取得した全タイトルリスト: {titles}")
        current_app.logger.info(f'スクレイピング結果のタイトル例 (最大10件):')
        for i, title_text in enumerate(titles[:10]):
            current_app.logger.info(f'  {i+1}: {title_text}')
        
        if len(titles) > 10:
            current_app.logger.info(f'  ... 他 {len(titles) - 10} 件')
    
    if not titles:
        current_app.logger.warning(f'キーワード "{keyword}" に一致するヘアスタイルが見つかりませんでした')
        return []
        
    # 非同期でテンプレート生成を実行
    current_app.logger.info(f'テンプレート生成開始: キーワード: "{keyword}", タイトル数: {len(titles)}, シーズン: "{season}", モデル: "{model}"')
    generator = TemplateGenerator(model_name=model)
    templates = await generator.generate_templates_async(titles, keyword, season, gender)
    
    current_app.logger.info(f'テンプレート生成成功 - {len(templates)}件のテンプレートを生成')
    
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
    
    return templates

@main_bp.route('/api/generate', methods=['POST'])
async def generate():
    """テンプレート生成のAPIエンドポイント"""
    try:
        # 不正なJSONリクエストの場合は400エラーを返す
        if request.is_json is False and request.data:
            current_app.logger.warning('不正なJSONリクエストを受信しました (Content-Typeが正しくないか、JSON形式ではありません)')
            return jsonify({
                'success': False,
                'error': {
                    'message': 'リクエストの形式が正しくありません。Content-Typeがapplication/jsonであること、有効なJSONであることを確認してください。',
                    'code': 'INVALID_JSON'
                },
                'status': 400
            }), 400
            
        data = request.get_json() # ここで BadRequest が発生する可能性があり、app_errorhandler(400) で処理される
        if data is None: # request.get_json() はパース失敗時にNoneを返すことがある (force=Falseの場合など)。通常はBadRequest。
            current_app.logger.warning('リクエストボディが空か、JSONとしてパースできませんでした。')
            return jsonify({
                'success': False,
                'error': {
                    'message': 'リクエストボディが空か、JSONとしてパースできませんでした。',
                    'code': 'INVALID_JSON'
                },
                'status': 400
            }), 400
        
        keyword = data.get('keyword')
        gender = data.get('gender', 'ladies')
        season = data.get('season') # 'none' や空文字の場合もありうる
        model = data.get('model', 'gemini-2.5-flash') # モデル選択（デフォルト）
        num_templates = int(data.get('num_templates', 5)) # この変数は現在 process_template_generation で使われていないが、将来のために残す
        
        current_app.logger.info(f'テンプレート生成リクエスト - キーワード: "{keyword}", 性別: "{gender}", シーズン: "{season}", モデル: "{model}", テンプレート数: {num_templates}')
        
        if not keyword:
            return jsonify({
                'success': False,
                'error': {
                    'message': 'キーワードを入力してください。',
                    'code': 'VALIDATION_ERROR'
                },
                'status': 400
            }), 400
            
        if gender not in ['ladies', 'mens']:
            return jsonify({
                'success': False,
                'error': {
                    'message': '無効な性別が指定されました。ladies または mens を指定してください。',
                    'code': 'VALIDATION_ERROR'
                },
                'status': 400
            }), 400
            
        # 非同期処理を直接 await
        templates = await process_template_generation(keyword, gender, season, model)
        
        if not templates:
            return jsonify({
                'success': False,
                'error': {
                    'message': '一致するヘアスタイルが見つかりませんでした。別のキーワードをお試しください。',
                    'code': 'NO_RESULTS_FOUND'
                },
                'status': 404 # 該当なしなので404
            }), 404
        
        return jsonify({
            'success': True,
            'templates': templates,
            'status': 200
        })
        
    except BadRequest as e:
        current_app.logger.warning(f'不正なJSONリクエスト (BadRequest例外): {str(e)}')
        # この例外は app_errorhandler(400) で処理されるので、ここでは再raiseするか、
        # もし app_errorhandler が期待通りに動作しない場合のフォールバックとして残す
        # 今回は app_errorhandler に処理を委ねるため、このブロックは理論上到達しないはず
        # ただし、より具体的なエラーコードを返したい場合はここで処理する
        return jsonify({
            'success': False,
            'error': {
                'message': f'リクエストの解析に失敗しました: {e.description if hasattr(e, "description") else str(e)}',
                'code': 'INVALID_JSON' # BadRequest は大抵JSON関連なので
            },
            'status': 400
        }), 400
        
    except ValueError as e:
        current_app.logger.warning(f'不正なリクエスト (ValueError): {str(e)}')
        return jsonify({
            'success': False,
            'error': {
                'message': f'リクエストデータが不正です: {str(e)}',
                'code': 'VALIDATION_ERROR' # ValueErrorは主にバリデーションエラーとして扱う
            },
            'status': 400
        }), 400
        
    except Exception as e:
        current_app.logger.error(f'テンプレート生成中に予期せぬエラー: {str(e)}', exc_info=True)
        # この例外は app_errorhandler(500) で処理されるので、ここでは再raiseするか、
        # もし app_errorhandler が期待通りに動作しない場合のフォールバックとして残す
        # 通常は app_errorhandler に任せる
        return jsonify({
            'success': False,
            'error': {
                'message': 'テンプレート生成中に予期せぬエラーが発生しました。',
                'code': 'INTERNAL_SERVER_ERROR'
            },
            'status': 500
        }), 500

# if __name__ == '__main__':
#     app.run(debug=True) # run.py から実行するため不要