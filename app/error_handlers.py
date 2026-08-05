"""アプリ全体のエラーハンドラ。

このアプリのエンドポイントは全て JSON を返す。フロントエンド（app/static/js/api.js）は
非 2xx でも本文を読んで error.code で案内を切り替えるため、
どの経路で失敗しても JSON になることが契約になる。

ルート側は例外を raise するだけでよく、レスポンスの組み立てはここに閉じている。
"""

import logging

from flask import Flask, request
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException

from .errors import AppError, ErrorCode, error_payload

logger = logging.getLogger(__name__)

# HTTPException のステータスごとの code と、ユーザーに見せる文言。
# werkzeug の description は英語なので、そのまま返さず日本語に置き換える。
# ここに無いステータスは下の既定へ寄せる。
_HTTP_ERRORS = {
    400: (ErrorCode.BAD_REQUEST, '不正なリクエストです。'),
    404: (ErrorCode.NOT_FOUND, 'リクエストされたページが見つかりません。'),
    405: (ErrorCode.BAD_REQUEST, 'このURLでは許可されていないメソッドです。'),
}


def _json(payload_and_status: tuple[dict, int]) -> ResponseReturnValue:
    payload, status = payload_and_status
    return payload, status


def register_error_handlers(app: Flask) -> None:
    """エラーハンドラをアプリに登録する。

    HTTPException と Exception は必ずセットで登録すること。
    Exception ハンドラだけを登録すると、Flask は 404 も Exception のサブクラスとして
    そちらへ流すため、存在しない URL が 500 になる。
    """

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError) -> ResponseReturnValue:
        if error.status_code >= 500:
            logger.error(f'{error.code}: {error.message}', exc_info=True)
        else:
            logger.warning(f'{error.code}: {error.message}')
        return _json(error.to_payload())

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> ResponseReturnValue:
        status = error.code or 500
        if status < 500:
            default = (ErrorCode.BAD_REQUEST, '不正なリクエストです。')
        else:
            default = (ErrorCode.INTERNAL_SERVER_ERROR, AppError.DEFAULT_MESSAGE)
        code, message = _HTTP_ERRORS.get(status, default)

        if status >= 500:
            logger.error(f'{code}: {error.description}', exc_info=True)
        else:
            logger.info(f'{code}: {request.path} - {error.description}')

        return _json(error_payload(message, code, status))

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> ResponseReturnValue:
        # 例外の中身はユーザーに出さない。原因はログの exc_info から追う。
        logger.error(f'予期しないエラー: {error}', exc_info=True)
        return _json(
            error_payload(
                AppError.DEFAULT_MESSAGE,
                ErrorCode.INTERNAL_SERVER_ERROR,
                500,
            )
        )
