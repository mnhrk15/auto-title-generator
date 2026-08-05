"""
Featured Keywords Manager

Beauty Selection特集キーワードの参照を担うモジュール。
JSONの読み込みと検証は featured_loader に委譲し、ここは保持と参照に専念する。
"""

import copy
import logging
import os
from typing import Any, Protocol

from flask import current_app

from . import config
from .featured_loader import load_featured_keywords

logger = logging.getLogger(__name__)

# Flask の app.extensions に登録する際のキー
EXTENSION_KEY = 'featured_keywords'


class FeaturedKeywordRepository(Protocol):
    """サービス層が依存する特集キーワードリポジトリの契約。

    型検査器は入れていないので強制力はない。実効的な検証は
    tests/conftest.py の FakeRepository が担う。
    ここに書く価値は「サービス層が実際に呼ぶのはこの 5 つだけ」を明示すること。
    """

    def is_available(self) -> bool: ...

    def get_keyword_info(self, keyword: str) -> dict | None: ...

    def get_all_keywords(self) -> list[dict]: ...

    def get_last_error(self) -> Exception | None: ...

    def get_health_status(self) -> dict[str, Any]: ...


class FeaturedKeywordsManager:
    """特集キーワードのリポジトリ

    起動時に一度 JSON を読み込み、以降は読み込み済みのデータを参照する。
    """

    def __init__(self, json_path=None):
        """FeaturedKeywordsManagerの初期化

        Args:
            json_path: 特集キーワードJSONファイルのパス。
                       省略時は config の既定値（パッケージ内の絶対パス）。
        """
        self.json_path = (
            json_path if json_path is not None else config.get_settings().featured_keywords_path
        )
        self.keywords: list[dict] = []
        self._last_error: Exception | None = None
        self._load_keywords()

    def _load_keywords(self) -> None:
        """JSONファイルから特集キーワードを読み込む

        エラーが発生した場合は空のリストを設定し、特集キーワード機能を無効化する。
        """
        self.keywords, self._last_error = load_featured_keywords(self.json_path)

    def is_featured_keyword(self, keyword: str) -> bool:
        """指定されたキーワードが特集キーワードかを判定する

        Args:
            keyword (str): 判定対象のキーワード

        Returns:
            bool: 特集キーワードの場合True、そうでなければFalse
        """
        return self.get_keyword_info(keyword) is not None

    def get_keyword_info(self, keyword: str) -> dict | None:
        """特集キーワードの詳細情報を取得する

        Args:
            keyword (str): 取得対象のキーワード

        Returns:
            Optional[Dict]: 特集キーワードの詳細情報。見つからない場合はNone
        """
        if not keyword or not isinstance(keyword, str):
            logger.debug(f"無効なキーワード入力: {keyword} (型: {type(keyword)})")
            return None

        if not self.keywords:
            logger.debug("特集キーワードが読み込まれていません")
            return None

        keyword_lower = keyword.lower().strip()
        if not keyword_lower:
            logger.debug("空のキーワードです")
            return None

        # keywords の各要素が keyword / name を持つ dict であることは
        # featured_loader._validate_item が保証済みなので、ここでの防御は不要。
        for item in self.keywords:
            if item['keyword'].lower().strip() == keyword_lower:
                logger.debug(f"特集キーワード情報取得成功: '{keyword}' -> '{item['name']}'")
                return copy.deepcopy(item)

        logger.debug(f"特集キーワード情報が見つかりません: '{keyword}'")
        return None

    def get_all_keywords(self) -> list[dict]:
        """すべての特集キーワード情報を取得する

        Returns:
            List[Dict]: すべての特集キーワードのリスト
        """
        return copy.deepcopy(self.keywords)

    def is_available(self) -> bool:
        """特集キーワード機能が利用可能かを確認する

        Returns:
            bool: 利用可能な場合True、そうでなければFalse
        """
        return len(self.keywords) > 0

    def get_last_error(self) -> Exception | None:
        """最後に発生したエラーを取得する

        Returns:
            Optional[Exception]: 最後に発生したエラー。エラーがない場合はNone
        """
        return self._last_error

    def get_health_status(self) -> dict[str, Any]:
        """特集キーワード機能の健全性状態を取得する

        Returns:
            Dict[str, Any]: 健全性状態の情報
        """
        return {
            'is_available': self.is_available(),
            'keywords_count': len(self.keywords),
            'file_path': str(self.json_path),
            'file_exists': os.path.exists(self.json_path),
            'last_error': str(self._last_error) if self._last_error else None,
            'error_type': type(self._last_error).__name__ if self._last_error else None,
        }


def get_featured_repository() -> FeaturedKeywordsManager:
    """現在のアプリに紐づく特集キーワードリポジトリを返す。

    サービス層はこれを直接呼ばず、引数でリポジトリを受け取ること
    （Flask コンテキストなしでテストできるようにするため）。
    """
    return current_app.extensions[EXTENSION_KEY]
