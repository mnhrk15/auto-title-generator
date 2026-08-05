"""アプリケーション共通のエラー定義。

レスポンス形状は既存のフロントエンド（app/static/js）が依存しているため変更しない::

    {'success': False, 'error': {'message': ..., 'code': ...}, 'status': N}

``AppError`` を送出すれば ``main.py`` の app_errorhandler が上記の形に変換する。
"""

from typing import Optional, Tuple


class ErrorCode:
    """API レスポンスの error.code に載せる値。"""

    INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR'
    NOT_FOUND = 'NOT_FOUND'
    BAD_REQUEST = 'BAD_REQUEST'
    INVALID_JSON = 'INVALID_JSON'
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    NO_RESULTS_FOUND = 'NO_RESULTS_FOUND'
    FEATURED_KEYWORDS_ERROR = 'FEATURED_KEYWORDS_ERROR'
    SCRAPING_ERROR = 'SCRAPING_ERROR'
    GENERATION_ERROR = 'GENERATION_ERROR'
    CONFIGURATION_ERROR = 'CONFIGURATION_ERROR'


def error_payload(message: str, code: str, status: int) -> Tuple[dict, int]:
    """エラーレスポンスの本文と HTTP ステータスを組み立てる。"""
    return {
        'success': False,
        'error': {
            'message': message,
            'code': code,
        },
        'status': status,
    }, status


class AppError(Exception):
    """ユーザーに返すエラーの基底クラス。

    サブクラスは code / status_code / DEFAULT_MESSAGE を定義する。
    """

    code = ErrorCode.INTERNAL_SERVER_ERROR
    status_code = 500
    DEFAULT_MESSAGE = 'サーバー内部でエラーが発生しました。しばらく時間をおいて再度お試しください。'

    def __init__(self, message: Optional[str] = None):
        self.message = message or self.DEFAULT_MESSAGE
        super().__init__(self.message)

    def to_payload(self) -> Tuple[dict, int]:
        return error_payload(self.message, self.code, self.status_code)


class ValidationError(AppError):
    """リクエスト内容が不正（ユーザー入力の誤り）。"""

    code = ErrorCode.VALIDATION_ERROR
    status_code = 400
    DEFAULT_MESSAGE = 'リクエストデータが不正です。'


class InvalidJsonError(AppError):
    """リクエストボディが JSON として解釈できない。"""

    code = ErrorCode.INVALID_JSON
    status_code = 400
    DEFAULT_MESSAGE = (
        'リクエストの形式が正しくありません。'
        'Content-Type が application/json であること、有効な JSON であることを確認してください。'
    )


class NoResultsError(AppError):
    """条件に一致するヘアスタイルが1件も見つからなかった。"""

    code = ErrorCode.NO_RESULTS_FOUND
    status_code = 404
    DEFAULT_MESSAGE = '一致するヘアスタイルが見つかりませんでした。別のキーワードをお試しください。'


class ScrapingError(AppError):
    """HotPepper Beauty への接続・取得に失敗した（外部要因）。"""

    code = ErrorCode.SCRAPING_ERROR
    status_code = 502
    DEFAULT_MESSAGE = (
        'HotPepper Beauty への接続に失敗しました。しばらく時間をおいて再度お試しください。'
    )


class GenerationError(AppError):
    """Gemini によるテンプレート生成に失敗した（外部要因）。"""

    code = ErrorCode.GENERATION_ERROR
    status_code = 502
    DEFAULT_MESSAGE = (
        'テンプレートの生成に失敗しました。しばらく時間をおいて再度お試しください。'
    )


class ConfigurationError(AppError):
    """サーバー側の設定不備（ユーザーの入力とは無関係）。"""

    code = ErrorCode.CONFIGURATION_ERROR
    status_code = 500
    DEFAULT_MESSAGE = 'サーバーの設定に問題があります。管理者にお問い合わせください。'


class FeaturedKeywordsError(AppError):
    """特集キーワード機能に関連するエラーの基底クラス。"""

    code = ErrorCode.FEATURED_KEYWORDS_ERROR
    status_code = 500
    DEFAULT_MESSAGE = '特集キーワード機能で問題が発生しています。管理者にお問い合わせください。'


class FeaturedKeywordsLoadError(FeaturedKeywordsError):
    """特集キーワードの読み込みに関するエラー。"""

    DEFAULT_MESSAGE = '特集キーワードファイルの読み込みに問題があります。管理者にお問い合わせください。'


class FeaturedKeywordsValidationError(FeaturedKeywordsError):
    """特集キーワードデータの検証に関するエラー。"""

    DEFAULT_MESSAGE = '特集キーワードデータに問題があります。管理者にお問い合わせください。'
