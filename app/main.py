import os
import logging
# import asyncio # Removed as run_async_task is deleted
from logging.handlers import RotatingFileHandler
from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.exceptions import BadRequest
from .scraping import HotPepperScraper
from .generator import TemplateGenerator
from .config import GEMINI_API_KEY
from .featured_keywords import FeaturedKeywordsManager
from . import featured_keywords

# Blueprintの作成
main_bp = Blueprint('main', __name__)

# FeaturedKeywordsManagerのインスタンス作成
featured_manager = FeaturedKeywordsManager()

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

@main_bp.route('/api/featured-keywords', methods=['GET'])
def get_featured_keywords():
    """特集キーワード一覧を取得するAPIエンドポイント（性別フィルタ対応）"""
    try:
        # リクエストパラメータから性別を取得
        gender = request.args.get('gender', 'ladies')  # デフォルトはレディース
        if gender not in ['ladies', 'mens']:
            gender = 'ladies'  # 無効な場合はレディースにフォールバック
            
        current_app.logger.info(f'特集キーワード取得リクエストを受信しました (性別: {gender})')
        
        # 特集キーワード機能の健全性チェック
        health_status = featured_manager.get_health_status()
        current_app.logger.debug(f'特集キーワード機能の状態: {health_status}')
        
        # 特集キーワード機能が利用可能かチェック
        if not featured_manager.is_available():
            last_error = featured_manager.get_last_error()
            if last_error:
                current_app.logger.warning(f'特集キーワード機能が利用できません: {last_error}')
                # エラーの種類に応じてメッセージを調整
                if isinstance(last_error, featured_keywords.FeaturedKeywordsLoadError):
                    message = '特集キーワードファイルの読み込みに問題があります。管理者にお問い合わせください。'
                elif isinstance(last_error, featured_keywords.FeaturedKeywordsValidationError):
                    message = '特集キーワードデータに問題があります。管理者にお問い合わせください。'
                else:
                    message = '特集キーワード機能で問題が発生しています。管理者にお問い合わせください。'
            else:
                current_app.logger.warning('特集キーワードが設定されていません')
                message = '現在、特集キーワードが設定されていません。'
            
            return jsonify({
                'success': True,
                'keywords': [],
                'message': message,
                'health_status': health_status,
                'status': 200
            }), 200
        
        # 特集キーワード一覧を取得
        all_keywords = featured_manager.get_all_keywords()
        current_app.logger.info(f'特集キーワードを取得しました: {len(all_keywords)}件（全性別）')
        
        # 指定された性別でフィルタリング
        filtered_keywords = [k for k in all_keywords if k.get('gender') == gender]
        current_app.logger.info(f'性別フィルタリング後: {len(filtered_keywords)}件 (対象: {gender})')
        
        # キーワードデータのサニタイズ（セキュリティ対策）
        sanitized_keywords = []
        for keyword in filtered_keywords:
            try:
                sanitized_keyword = {
                    'name': str(keyword.get('name', '')).strip(),
                    'keyword': str(keyword.get('keyword', '')).strip(),
                    'gender': str(keyword.get('gender', 'ladies')).strip(),
                    'condition': str(keyword.get('condition', '')).strip()
                }
                # 空のフィールドをチェック
                if all(sanitized_keyword.values()):
                    sanitized_keywords.append(sanitized_keyword)
                else:
                    current_app.logger.warning(f'不完全な特集キーワードデータをスキップ: {keyword}')
            except Exception as e:
                current_app.logger.warning(f'特集キーワードデータのサニタイズ中にエラー: {e}')
                continue
        
        return jsonify({
            'success': True,
            'keywords': sanitized_keywords,
            'gender': gender,
            'total_keywords': len(all_keywords),
            'filtered_keywords': len(sanitized_keywords),
            'health_status': health_status,
            'status': 200
        })
        
    except Exception as e:
        current_app.logger.error(f'特集キーワード取得中に予期しないエラーが発生しました: {str(e)}', exc_info=True)
        
        # フォールバック: 空のキーワードリストを返して通常機能を継続
        return jsonify({
            'success': True,  # フォールバックなのでsuccessはTrue
            'keywords': [],
            'message': '特集キーワードの取得に失敗しましたが、通常の機能は利用できます。',
            'fallback': True,
            'error': {
                'message': '特集キーワードの取得に失敗しました。',
                'code': 'FEATURED_KEYWORDS_ERROR'
            },
            'status': 200
        }), 200

# スクレイピングと生成を非同期で行う関数
async def process_template_generation(keyword: str, gender: str, season: str = None, model: str = 'gemini-2.5-flash') -> list:
    """スクレイピングとテンプレート生成を非同期で処理する"""
    current_app.logger.info(f'非同期処理開始: キーワード: "{keyword}", 性別: "{gender}", シーズン: "{season}", モデル: "{model}"')
    
    # 混在キーワード処理の実装（特集キーワードと通常キーワードの適切な判定処理）
    is_featured = False
    featured_info = None
    keyword_type = "normal"  # "featured", "normal", "mixed", "error"
    processing_mode = "standard"  # "featured", "standard", "fallback"
    
    try:
        # キーワードの前処理（空白の除去、正規化、複数キーワード対応）
        normalized_keyword = keyword.strip() if keyword else ""
        
        if not normalized_keyword:
            current_app.logger.warning('空のキーワードが入力されました - 通常処理を継続')
            keyword_type = "normal"
            processing_mode = "standard"
        else:
            # 複数キーワードの検出（スペース、カンマ、スラッシュで区切られた場合）
            keyword_separators = [' ', '　', ',', '、', '/', '＋', '+']
            multiple_keywords = [normalized_keyword]  # デフォルトは単一キーワード
            
            for separator in keyword_separators:
                if separator in normalized_keyword:
                    multiple_keywords = [kw.strip() for kw in normalized_keyword.split(separator) if kw.strip()]
                    current_app.logger.info(f'複数キーワードを検出しました: {multiple_keywords}')
                    break
            
            # 特集キーワード機能が利用可能かチェック
            if featured_manager.is_available():
                featured_keywords_found = []
                normal_keywords_found = []
                
                # 各キーワードを個別に判定
                for kw in multiple_keywords:
                    kw_normalized = kw.strip()
                    if not kw_normalized:
                        continue
                        
                    if featured_manager.is_featured_keyword(kw_normalized):
                        kw_info = featured_manager.get_keyword_info(kw_normalized)
                        if kw_info:
                            featured_keywords_found.append({
                                'keyword': kw_normalized,
                                'info': kw_info
                            })
                            current_app.logger.info(f'特集キーワードを検出: "{kw_normalized}" -> "{kw_info["name"]}" (性別: {kw_info["gender"]})')
                        else:
                            current_app.logger.warning(f'特集キーワード "{kw_normalized}" の詳細情報取得に失敗')
                            normal_keywords_found.append(kw_normalized)
                    else:
                        normal_keywords_found.append(kw_normalized)
                        current_app.logger.debug(f'通常キーワード: "{kw_normalized}"')
                
                # 混在キーワード処理の分岐ロジック
                if featured_keywords_found and normal_keywords_found:
                    # 混在ケース: 特集キーワードと通常キーワードが混在
                    keyword_type = "mixed"
                    processing_mode = "featured"  # 特集キーワードを優先
                    
                    # 最初の特集キーワードを使用（複数ある場合は最初のものを優先）
                    primary_featured = featured_keywords_found[0]
                    is_featured = True
                    featured_info = primary_featured['info']
                    
                    current_app.logger.info(f'混在キーワード処理: 特集キーワード "{primary_featured["keyword"]}" を優先使用')
                    current_app.logger.info(f'併用される通常キーワード: {normal_keywords_found}')
                    
                    # 性別整合性チェック（混在時は特集キーワードの性別を優先）
                    if featured_info["gender"] != gender:
                        current_app.logger.warning(f'混在処理: 特集キーワード "{primary_featured["keyword"]}" の対象性別 ({featured_info["gender"]}) と入力された性別 ({gender}) が一致しません')
                        current_app.logger.info(f'混在処理: 特集キーワードの性別設定を優先して処理を継続します')
                
                elif featured_keywords_found and not normal_keywords_found:
                    # 純粋な特集キーワードケース
                    keyword_type = "featured"
                    processing_mode = "featured"
                    
                    # 複数の特集キーワードがある場合は最初のものを使用
                    primary_featured = featured_keywords_found[0]
                    is_featured = True
                    featured_info = primary_featured['info']
                    
                    current_app.logger.info(f'純粋特集キーワード処理: "{primary_featured["keyword"]}" -> "{featured_info["name"]}" (性別: {featured_info["gender"]})')
                    
                    if len(featured_keywords_found) > 1:
                        other_featured = [f['keyword'] for f in featured_keywords_found[1:]]
                        current_app.logger.info(f'その他の特集キーワード（参考情報として記録）: {other_featured}')
                    
                    # 性別整合性チェック
                    if featured_info["gender"] != gender:
                        current_app.logger.warning(f'特集キーワード "{primary_featured["keyword"]}" の対象性別 ({featured_info["gender"]}) と入力された性別 ({gender}) が一致しません')
                        # 性別が一致しない場合でも特集キーワードとして処理を継続（要件に基づく）
                
                elif not featured_keywords_found and normal_keywords_found:
                    # 純粋な通常キーワードケース
                    keyword_type = "normal"
                    processing_mode = "standard"
                    is_featured = False
                    featured_info = None
                    
                    current_app.logger.info(f'純粋通常キーワード処理: {normal_keywords_found}')
                
                else:
                    # 有効なキーワードが見つからない場合
                    keyword_type = "error"
                    processing_mode = "fallback"
                    is_featured = False
                    featured_info = None
                    
                    current_app.logger.warning(f'有効なキーワードが見つかりませんでした: "{normalized_keyword}"')
                    
            else:
                # 特集キーワード機能が利用できない場合
                keyword_type = "normal"
                processing_mode = "standard"
                is_featured = False
                featured_info = None
                
                current_app.logger.info(f'特集キーワード機能が利用できません - 通常キーワードとして処理: "{normalized_keyword}"')
                
    except Exception as e:
        current_app.logger.error(f'キーワード判定中にエラー: {str(e)} - 通常処理にフォールバック')
        keyword_type = "error"
        processing_mode = "fallback"
        is_featured = False
        featured_info = None
    
    # 処理分岐ロジックの実装と動作保証
    current_app.logger.info(f'キーワード処理結果: タイプ={keyword_type}, モード={processing_mode}, 特集対応={is_featured}')
    
    # 両方のケースでの適切な動作を保証するための詳細ログ
    if processing_mode == "featured":
        if keyword_type == "mixed":
            current_app.logger.info(f'混在キーワード処理パス: 特集キーワード優先で強化プロンプトを使用')
            current_app.logger.info(f'使用する特集情報: {featured_info["name"]} (条件: {featured_info["condition"][:50]}...)')
        else:
            current_app.logger.info(f'特集キーワード処理パス: 強化プロンプトを使用してテンプレート生成を実行')
            current_app.logger.info(f'特集情報: {featured_info["name"]} (条件: {featured_info["condition"][:50]}...)')
    elif processing_mode == "standard":
        current_app.logger.info(f'通常キーワード処理パス: 標準プロンプトを使用してテンプレート生成を実行')
    elif processing_mode == "fallback":
        current_app.logger.info(f'フォールバック処理パス: エラー回復のため標準プロンプトを使用')
    
    # 処理モードの妥当性確認
    if processing_mode not in ["featured", "standard", "fallback"]:
        current_app.logger.error(f'不正な処理モード: {processing_mode} - 標準モードにフォールバック')
        processing_mode = "standard"
        is_featured = False
        featured_info = None
    
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
        
    # 非同期でテンプレート生成を実行（特集情報と処理モード情報を渡す）
    current_app.logger.info(f'テンプレート生成開始: キーワード: "{keyword}", タイトル数: {len(titles)}, シーズン: "{season}", モデル: "{model}", 特集対応: {is_featured}, 処理モード: {processing_mode}')
    generator = TemplateGenerator(model_name=model)
    
    # 混在キーワード処理のための追加情報を準備
    generation_context = {
        'keyword_type': keyword_type,
        'processing_mode': processing_mode,
        'original_keyword': keyword,
        'normalized_keyword': normalized_keyword if 'normalized_keyword' in locals() else keyword
    }
    
    templates = await generator.generate_templates_async(
        titles, 
        keyword, 
        season, 
        gender, 
        featured_info=featured_info,
        generation_context=generation_context
    )
    
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
    
    # 特集対応テンプレート識別機能の実装（混在キーワード処理対応）
    # 生成されたテンプレートが特集対応かを示すフラグを追加
    for template in templates:
        template['is_featured'] = is_featured
        template['keyword_type'] = keyword_type
        template['processing_mode'] = processing_mode
        template['original_keyword'] = keyword
        
        # 特集キーワード情報も含める（デバッグ用）
        if is_featured and featured_info:
            template['featured_keyword_name'] = featured_info.get('name', '')
            template['featured_condition'] = featured_info.get('condition', '')
            template['featured_gender'] = featured_info.get('gender', '')
        
        # 混在キーワード処理の場合の追加情報
        if keyword_type == "mixed":
            template['is_mixed_keyword'] = True
            template['mixed_processing_note'] = '特集キーワードと通常キーワードが混在しています'
        else:
            template['is_mixed_keyword'] = False
    
    # 混在処理の結果をログに記録
    if keyword_type == "mixed":
        current_app.logger.info(f'混在キーワードテンプレート生成完了: {len(templates)}件 (元キーワード: "{keyword}", 優先特集: "{featured_info.get("name", "不明")}", 処理モード: {processing_mode})')
    elif is_featured:
        current_app.logger.info(f'特集対応テンプレート生成完了: {len(templates)}件 (キーワード: "{keyword}" -> "{featured_info.get("name", "不明")}", 処理モード: {processing_mode})')
    else:
        current_app.logger.info(f'通常テンプレート生成完了: {len(templates)}件 (キーワード: "{keyword}", 処理モード: {processing_mode})')
    
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
        
        # 混在キーワード処理情報を含むレスポンス
        template_metadata = templates[0] if templates else {}
        response_keyword_type = template_metadata.get('keyword_type', 'normal')
        response_processing_mode = template_metadata.get('processing_mode', 'standard')
        response_is_featured = template_metadata.get('is_featured', False)
        response_is_mixed = template_metadata.get('is_mixed_keyword', False)
        
        # 特集キーワード情報の取得（混在処理対応）
        featured_keyword_info = None
        if response_is_featured and template_metadata.get('featured_keyword_name'):
            featured_keyword_info = {
                'name': template_metadata.get('featured_keyword_name', ''),
                'condition': template_metadata.get('featured_condition', ''),
                'gender': template_metadata.get('featured_gender', '')
            }
        
        return jsonify({
            'success': True,
            'templates': templates,
            'is_featured': response_is_featured,
            'keyword_type': response_keyword_type,
            'processing_mode': response_processing_mode,
            'is_mixed_keyword': response_is_mixed,
            'original_keyword': keyword,
            'featured_keyword_info': featured_keyword_info,
            'processing_summary': {
                'total_templates': len(templates),
                'keyword_analysis': response_keyword_type,
                'processing_path': response_processing_mode,
                'mixed_keyword_detected': response_is_mixed
            },
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