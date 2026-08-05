"""特集キーワード JSON の読み込みと検証。

Flask に依存しない純粋な関数として切り出してある。
リポジトリ（FeaturedKeywordsManager）は結果を保持するだけで、
ファイル I/O と検証ロジックはすべてここに閉じている。
"""

import json
import logging
import os
import traceback
from typing import NamedTuple

from . import config
from .errors import FeaturedKeywordsLoadError, FeaturedKeywordsValidationError

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ('name', 'keyword', 'gender', 'condition')

# ログに出す検証エラーの最大件数（全件出すとノイズになるため）
MAX_LOGGED_VALIDATION_ERRORS = 5


class LoadResult(NamedTuple):
    """読み込み結果。

    keywords が空でも error が None のことがある（ファイルが空配列の場合など）。
    """

    keywords: list[dict]
    error: Exception | None


def _validate_item(item, index: int) -> str | None:
    """1件分のキーワードを検証する。

    Returns:
        Optional[str]: 問題があればエラー文言、問題なければ None
    """
    if not isinstance(item, dict):
        return f"特集キーワード[{index}]: 辞書形式ではありません"

    missing_fields = [f for f in REQUIRED_FIELDS if f not in item or not item[f]]
    if missing_fields:
        return f"特集キーワード[{index}]: 必須フィールドが不足または空です: {missing_fields}"

    # 型を先に確認する。これを飛ばすと後段の len() や .lower() が TypeError を送出し、
    # 「1件だけスキップして継続する」という本モジュールの契約を破ってしまう。
    non_str_fields = [f for f in REQUIRED_FIELDS if not isinstance(item[f], str)]
    if non_str_fields:
        return f"特集キーワード[{index}]: 文字列でないフィールドがあります: {non_str_fields}"

    if item['gender'] not in config.GENDERS:
        return f"特集キーワード[{index}]: 不正な性別値 '{item['gender']}'"

    length_limits = (
        ('name', '名前', config.FEATURED_NAME_MAX),
        ('keyword', 'キーワード', config.FEATURED_KEYWORD_MAX),
        ('condition', '条件文', config.FEATURED_CONDITION_MAX),
    )
    for field, label, limit in length_limits:
        if len(item[field]) > limit:
            return (
                f"特集キーワード[{index}]: {label}が長すぎます ({len(item[field])} > {limit}文字)"
            )

    return None


def _read_file(path) -> list:
    """JSON ファイルを読み込む。事前にサイズと存在を検証する。"""
    if not os.path.exists(path):
        raise FeaturedKeywordsLoadError(f"特集キーワードファイルが見つかりません: {path}")

    file_size = os.path.getsize(path)
    if file_size == 0:
        raise FeaturedKeywordsLoadError(f"特集キーワードファイルが空です: {path}")

    if file_size > config.FEATURED_FILE_MAX_BYTES:
        raise FeaturedKeywordsLoadError(f"特集キーワードファイルが大きすぎます: {file_size} bytes")

    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_featured_keywords(path) -> LoadResult:
    """特集キーワードを読み込んで検証する。

    例外は送出せず、失敗は LoadResult.error に載せて返す。
    特集キーワードは付加的な機能であり、読み込み失敗でアプリ全体を止めないため。
    """
    try:
        logger.info(f"特集キーワードファイルの読み込みを開始: {path}")
        data = _read_file(path)
    except FeaturedKeywordsLoadError as e:
        logger.warning(str(e))
        return LoadResult([], e)
    except json.JSONDecodeError as e:
        error = FeaturedKeywordsLoadError(f"特集キーワードファイルのJSON形式が不正です: {str(e)}")
        logger.error(str(error))
        logger.debug(f"JSONDecodeError詳細: {traceback.format_exc()}")
        return LoadResult([], error)
    except PermissionError as e:
        error = FeaturedKeywordsLoadError(
            f"特集キーワードファイルの読み込み権限がありません: {str(e)}"
        )
        logger.error(str(error))
        return LoadResult([], error)
    except UnicodeDecodeError as e:
        error = FeaturedKeywordsLoadError(
            f"特集キーワードファイルの文字エンコーディングエラー: {str(e)}"
        )
        logger.error(str(error))
        return LoadResult([], error)
    except Exception as e:
        error = FeaturedKeywordsLoadError(f"特集キーワード読み込み中に予期しないエラー: {str(e)}")
        logger.error(str(error))
        logger.debug(f"予期しないエラー詳細: {traceback.format_exc()}")
        return LoadResult([], error)

    if not isinstance(data, list):
        error = FeaturedKeywordsValidationError(
            "特集キーワードファイルの形式が不正です: ルート要素は配列である必要があります"
        )
        logger.error(str(error))
        return LoadResult([], error)

    if not data:
        # 空のファイルはエラーではない（特集がない期間を表現できる）
        logger.warning("特集キーワードファイルに有効なデータがありません")
        return LoadResult([], None)

    validated: list[dict] = []
    seen_keywords = set()
    validation_errors: list[str] = []

    for index, item in enumerate(data):
        # 検証中の想定外の例外で読み込み全体を落とさない（該当の1件だけスキップする）。
        # このファイルは運用者が手で編集するため、1件のタイポでアプリが起動不能になるのを避ける。
        try:
            error_msg = _validate_item(item, index)

            if error_msg is None:
                normalized = item['keyword'].lower().strip()
                if normalized in seen_keywords:
                    error_msg = f"特集キーワード[{index}]: 重複するキーワード '{item['keyword']}'"
                else:
                    seen_keywords.add(normalized)
        except Exception as e:
            error_msg = f"特集キーワード[{index}]の検証中にエラー: {str(e)}"

        if error_msg is not None:
            logger.warning(f"{error_msg} - スキップします")
            validation_errors.append(error_msg)
            continue

        validated.append(item)
        logger.debug(f"特集キーワード[{index}]を検証完了: {item['name']}")

    if validation_errors:
        logger.warning(
            f"特集キーワード読み込み完了（警告あり）: "
            f"有効 {len(validated)}件, エラー {len(validation_errors)}件"
        )
        for error_msg in validation_errors[:MAX_LOGGED_VALIDATION_ERRORS]:
            logger.warning(f"  - {error_msg}")
        remaining = len(validation_errors) - MAX_LOGGED_VALIDATION_ERRORS
        if remaining > 0:
            logger.warning(f"  - ... 他 {remaining} 件のエラー")
    else:
        logger.info(f"特集キーワードを正常に読み込みました: {len(validated)}件")

    return LoadResult(validated, None)
