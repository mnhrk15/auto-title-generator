import logging
from dataclasses import dataclass

from flask import Blueprint, jsonify, render_template, request
from flask.typing import ResponseReturnValue

from .config import DEFAULT_MODEL, GENDERS
from .errors import InvalidJsonError, ValidationError
from .featured_keywords import get_featured_repository
from .seasons import normalize_seasons
from .services.featured_service import list_featured_keywords
from .services.template_service import GenerationOutcome, generate_templates_for_request

# app/__init__.py が root ロガーにハンドラを付けているので、
# current_app.logger を使わなくても出力先は同じになる。
# モジュールロガーにしておくと、ルートの処理をアプリコンテキストなしでも呼べる。
logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@dataclass(frozen=True)
class GenerateRequest:
    """/api/generate のリクエスト。

    seasons は正規化済みであることを型で保証する。
    正規化の所有者は parse_generate_request の 1 箇所だけ。
    """

    keyword: str
    gender: str
    seasons: list[str]
    model: str


def parse_generate_request(data: object) -> GenerateRequest:
    """リクエストボディを検証して GenerateRequest にする。

    Flask に依存しないので単体でテストできる。

    Raises:
        InvalidJsonError: ボディが JSON オブジェクトでない
        ValidationError: 値が不正
    """
    if not isinstance(data, dict):
        raise InvalidJsonError()

    keyword = data.get('keyword')
    if not keyword:
        raise ValidationError('キーワードを入力してください。')

    gender = data.get('gender', 'ladies')
    if gender not in GENDERS:
        raise ValidationError('無効な性別が指定されました。ladies または mens を指定してください。')

    seasons = data.get('seasons') or []
    if not isinstance(seasons, list):
        raise ValidationError('季節・カラーの指定形式が正しくありません。配列で指定してください。')

    return GenerateRequest(
        keyword=keyword,
        gender=gender,
        # 未知の値と重複を除き、config の定義順に揃える。
        # メンズでは季節カラー／ブリーチなしカラーを扱わないため常に空になる。
        seasons=normalize_seasons(seasons, gender),
        model=data.get('model', DEFAULT_MODEL),
    )


def _featured_keyword_info(outcome: GenerationOutcome) -> dict | None:
    """フロントエンドが表示に使う特集キーワード情報。"""
    if not outcome.is_featured or not outcome.featured_info:
        return None
    return {
        'name': outcome.featured_info.get('name', ''),
        'condition': outcome.featured_info.get('condition', ''),
        'gender': outcome.featured_info.get('gender', ''),
    }


@main_bp.route('/')
def index() -> str:
    """トップページのルート"""
    logger.info('トップページにアクセスがありました')
    return render_template('index.html')


@main_bp.route('/api/featured-keywords', methods=['GET'])
def get_featured_keywords() -> ResponseReturnValue:
    """特集キーワード一覧を取得するAPIエンドポイント（性別フィルタ対応）"""
    gender = request.args.get('gender', 'ladies')
    if gender not in GENDERS:
        raise ValidationError('無効な性別が指定されました。ladies または mens を指定してください。')

    logger.info(f'特集キーワード取得リクエストを受信しました (性別: {gender})')

    view = list_featured_keywords(get_featured_repository(), gender)

    return jsonify(
        {
            'success': True,
            'keywords': view.keywords,
            # 降格時のみ文言が入る。フロントエンドは常にこのキーを読む。
            'message': view.message,
        }
    )


@main_bp.route('/api/generate', methods=['POST'])
async def generate() -> ResponseReturnValue:
    """テンプレート生成のAPIエンドポイント"""
    req = parse_generate_request(request.get_json(silent=True))

    logger.info(
        f'テンプレート生成リクエスト - キーワード: "{req.keyword}", 性別: "{req.gender}", '
        f'季節・カラー選択: {req.seasons}, モデル: "{req.model}"'
    )

    outcome = await generate_templates_for_request(
        req.keyword,
        req.gender,
        repository=get_featured_repository(),
        seasons=req.seasons,
        model=req.model,
    )

    return jsonify(
        {
            'success': True,
            'templates': outcome.templates,
            'is_featured': outcome.is_featured,
            'featured_keyword_info': _featured_keyword_info(outcome),
        }
    )
