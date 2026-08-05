from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.exceptions import BadRequest
from .config import DEFAULT_MODEL, GENDERS, normalize_seasons
from .errors import (
    AppError,
    ErrorCode,
    InvalidJsonError,
    NoResultsError,
    ValidationError,
    error_payload,
)
from .featured_keywords import get_featured_repository
from . import featured_keywords
from .services.template_service import generate_templates_for_request

# Blueprintの作成
main_bp = Blueprint('main', __name__)

# エラーハンドラー
@main_bp.app_errorhandler(AppError)
def app_error(error: AppError):
    """AppError を統一フォーマットの JSON レスポンスに変換する"""
    if error.status_code >= 500:
        current_app.logger.error(f'{error.code}: {error.message}', exc_info=True)
    else:
        current_app.logger.warning(f'{error.code}: {error.message}')

    payload, status = error.to_payload()
    return jsonify(payload), status

@main_bp.app_errorhandler(500)
def internal_error(error):
    current_app.logger.error(f'サーバーエラー: {str(error)}')
    payload, status = error_payload(
        'サーバー内部でエラーが発生しました。しばらく時間をおいて再度お試しください。',
        ErrorCode.INTERNAL_SERVER_ERROR,
        500,
    )
    return jsonify(payload), status

@main_bp.app_errorhandler(404)
def not_found_error(error):
    current_app.logger.info(f'ページが見つかりません: {request.url}')
    payload, status = error_payload(
        'リクエストされたページが見つかりません。',
        ErrorCode.NOT_FOUND,
        404,
    )
    return jsonify(payload), status

@main_bp.app_errorhandler(400)
def bad_request_error(error):
    # BadRequest 例外から元のメッセージを取得しようと試みる
    # werkzeug.exceptions.BadRequest は description 属性にメッセージを持つ
    message = str(error)
    if hasattr(error, 'description') and error.description:
        message = error.description

    current_app.logger.warning(f'不正なリクエスト: {message}')
    payload, status = error_payload(
        f'不正なリクエストです: {message}',
        ErrorCode.BAD_REQUEST,
        400,
    )
    return jsonify(payload), status

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
        if gender not in GENDERS:
            gender = 'ladies'  # 無効な場合はレディースにフォールバック
            
        current_app.logger.info(f'特集キーワード取得リクエストを受信しました (性別: {gender})')

        repository = get_featured_repository()

        # 特集キーワード機能の健全性チェック
        health_status = repository.get_health_status()
        current_app.logger.debug(f'特集キーワード機能の状態: {health_status}')

        # 特集キーワード機能が利用可能かチェック
        if not repository.is_available():
            last_error = repository.get_last_error()
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

            # 「リクエスト自体は成功したが機能が降格している」状態なので success は True。
            # フロントエンドはこれを受けて通常のテンプレート生成を継続できる。
            return jsonify({
                'success': True,
                'keywords': [],
                'message': message,
                'health_status': health_status,
                'status': 200
            }), 200
        
        # 特集キーワード一覧を取得
        all_keywords = repository.get_all_keywords()
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

        # 以前は success: True と error オブジェクトを同時に返していたが、
        # 「成功」と「エラー」が同時に成立するのは矛盾しており、フロントエンドは
        # success だけを見て成功扱いしていた。失敗は失敗として返す。
        payload, status = error_payload(
            '特集キーワードの取得に失敗しました。通常のテンプレート生成はご利用いただけます。',
            ErrorCode.FEATURED_KEYWORDS_ERROR,
            503,
        )
        return jsonify(payload), status

@main_bp.route('/api/generate', methods=['POST'])
async def generate():
    """テンプレート生成のAPIエンドポイント"""
    try:
        # 不正なJSONリクエストの場合は400エラーを返す
        if request.is_json is False and request.data:
            raise InvalidJsonError()

        data = request.get_json() # ここで BadRequest が発生する可能性があり、app_errorhandler(400) で処理される
        if data is None: # request.get_json() はパース失敗時にNoneを返すことがある (force=Falseの場合など)。通常はBadRequest。
            raise InvalidJsonError('リクエストボディが空か、JSONとしてパースできませんでした。')

        keyword = data.get('keyword')
        gender = data.get('gender', 'ladies')
        seasons = data.get('seasons', []) # 季節・カラーのチェックボックス選択（複数可・省略可）
        model = data.get('model', DEFAULT_MODEL) # モデル選択（デフォルト）

        if seasons is None:
            seasons = []
        if not isinstance(seasons, list):
            raise ValidationError('季節・カラーの指定形式が正しくありません。配列で指定してください。')

        current_app.logger.info(f'テンプレート生成リクエスト - キーワード: "{keyword}", 性別: "{gender}", 季節・カラー選択: {seasons}, モデル: "{model}"')

        if not keyword:
            raise ValidationError('キーワードを入力してください。')

        if gender not in GENDERS:
            raise ValidationError('無効な性別が指定されました。ladies または mens を指定してください。')

        # 季節・カラー選択の正規化（未知の値と重複を除去し、config の定義順に揃える）
        # メンズでは季節カラー／ブリーチなしカラーを扱わないため常に無効化する
        seasons = normalize_seasons(seasons, gender)

        # 非同期処理を直接 await
        templates, trending_keywords = await generate_templates_for_request(
            keyword,
            gender,
            repository=get_featured_repository(),
            seasons=seasons,
            model=model,
        )

        if not templates:
            raise NoResultsError()


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
            'trending_keywords': trending_keywords,
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
        
    except AppError:
        # app_errorhandler(AppError) が統一フォーマットに変換する
        raise

    except BadRequest as e:
        # request.get_json() のパース失敗。JSON 関連なので INVALID_JSON として返す
        description = e.description if hasattr(e, 'description') else str(e)
        raise InvalidJsonError(f'リクエストの解析に失敗しました: {description}') from e

    except Exception as e:
        # ValueError を一律 400 に丸めると、サーバー設定の不備までユーザー入力エラーとして
        # 返してしまうため、想定外の例外はすべて 500 として扱う
        current_app.logger.error(f'テンプレート生成中に予期せぬエラー: {str(e)}', exc_info=True)
        payload, status = error_payload(
            'テンプレート生成中に予期せぬエラーが発生しました。',
            ErrorCode.INTERNAL_SERVER_ERROR,
            500,
        )
        return jsonify(payload), status