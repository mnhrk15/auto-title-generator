"""生成されたテンプレートの検証。

文字数制限は HotPepper Beauty の掲載仕様に由来する。
I/O を持たないので API キーなしでテストできる。
"""

import logging

from . import config

logger = logging.getLogger(__name__)

REQUIRED_KEYS = ('title', 'menu', 'comment', 'hashtag')


def validate_template(template: dict[str, str], keyword: str) -> bool:
    """テンプレートの文字数制限チェックとキーワード含有チェック"""
    try:
        for key in REQUIRED_KEYS:
            if key not in template:
                logger.warning(f"テンプレートに必須キー '{key}' がありません")
                return False

        # キーワードが含まれていなくてもテンプレートは有効とする。
        # 含有を必須にすると、言い換えや語順の入れ替えで軒並み落ちてしまう。
        if keyword.lower() not in template['title'].lower():
            logger.warning(
                f"タイトルにキーワード '{keyword}' が含まれていません: {template['title']}"
            )

        for key, limit in config.CHAR_LIMITS.items():
            if key == 'hashtag':
                # ハッシュタグは配列なので個別に見る（下のループ）
                continue

            if len(template[key]) > limit:
                logger.warning(f"{key}の文字数が制限を超えています: {len(template[key])} > {limit}")
                return False

        if not isinstance(template['hashtag'], list):
            logger.warning(f"ハッシュタグがリスト形式ではありません: {type(template['hashtag'])}")
            return False

        if len(template['hashtag']) < config.HASHTAG_MIN_COUNT:
            logger.warning(
                f"ハッシュタグの数が少なすぎます: "
                f"{len(template['hashtag'])} < {config.HASHTAG_MIN_COUNT}"
            )
            return False

        for tag in template['hashtag']:
            if len(tag) > config.CHAR_LIMITS['hashtag']:
                logger.warning(
                    f"ハッシュタグが長すぎます: {tag} "
                    f"({len(tag)} > {config.CHAR_LIMITS['hashtag']})"
                )
                return False

        logger.debug(f"テンプレート検証成功: '{template['title']}'")
        return True
    except (KeyError, AttributeError, TypeError) as e:
        # TypeError: 値が文字列以外（数値・None など）で len() に失敗するケース
        logger.error(f"テンプレート検証エラー: {str(e)}")
        return False
