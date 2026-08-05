"""季節・カラーキーワードの正規化と、タイトルへの付加。

Gemini のプロンプトには季節・カラーを一切入れず、生成後に Python 側で付加する。
プロンプトに入れるとモデルが解釈を広げてしまい、選択されていない色まで出てくるため。

I/O を持たない純粋なロジックなので、API キーなしでテストできる。
"""

import logging
from collections.abc import Sequence

from . import config

logger = logging.getLogger(__name__)


def normalize_seasons(seasons: Sequence[str] | None, gender: str) -> list[str]:
    """季節・カラー選択値を config の定義順に正規化する（未知値と重複を除去）。

    メンズでは季節カラー／ブリーチなしカラーを一切扱わないため常に空リストを返す。

    正規化の呼び出しはリクエストあたり 1 回（main.parse_generate_request）に限る。
    以前はルート・生成器・プロンプト組み立ての 3 箇所で呼ばれており、
    「どこで正規化済みになるのか」が不明瞭だった。
    """
    return config.normalize_seasons(seasons, gender)


def _pick_separator(title: str, rotation_index: int) -> tuple[str, int]:
    """タイトルに付ける区切り記号と、次のローテーション位置を返す"""
    # タイトルがすでに使っている区切り記号に合わせる（複数あれば末尾に近いもの）
    matched = max(
        (d for d in config.SEASON_APPEND_DELIMITERS if d in title),
        key=title.rfind,
        default=None,
    )
    if matched is not None:
        return matched, rotation_index

    # 記号なしのタイトルには記号を順番に割り当てる（すでに含む記号は避ける）
    rotation = config.SEASON_APPEND_SEPARATORS
    separator = rotation[rotation_index % len(rotation)]
    for _ in range(len(rotation)):
        separator = rotation[rotation_index % len(rotation)]
        rotation_index += 1
        if separator not in title:
            break
    return separator, rotation_index


def apply_season_keywords(templates: list[dict[str, str]], seasons: Sequence[str]) -> None:
    """選択された季節・カラーキーワードをタイトルへ付加する（テンプレートを直接書き換える）

    - SEASON_APPEND_THRESHOLD 文字未満のタイトルのみが対象
    - 付加後に上限文字数を超える場合は付加しない
    - 複数選択時は対象タイトルへ均等に配分する
    - 各キーワードには、収まる範囲で最も長いタイトル＝上限文字数に最も近づくものを割り当てる
    - 区切り記号はタイトルが使っている記号に合わせ、記号がなければローテーションする

    呼び出し側は渡したリストの中身が書き換わることを前提にしている（戻り値はない）。
    """
    if not seasons or not templates:
        return

    # 重複があると割り当てループのキーワード集合が空になりうるため、ここでも重複を除く
    seasons = list(dict.fromkeys(seasons))

    title_limit = config.CHAR_LIMITS['title']
    # 区切り記号は全て1文字だが、将来増えても破綻しないよう最長で見積もる
    separator_length = max(
        len(s) for s in config.SEASON_APPEND_SEPARATORS + config.SEASON_APPEND_DELIMITERS
    )
    keywords = {key: config.SEASON_COLOR_CHOICES[key] for key in seasons}
    counts = {key: 0 for key in seasons}
    priority = {key: i for i, key in enumerate(seasons)}
    rotation_index = 0

    # 付加対象を長い順に並べる。キーワードごとに「収まる中で最も長いタイトル」を取れるようにするため
    remaining = sorted(
        (t for t in templates if len(t.get('title', '')) < config.SEASON_APPEND_THRESHOLD),
        key=lambda t: len(t.get('title', '')),
        reverse=True,
    )

    # タイトル側ではなくキーワード側から割り当てる。
    # 付加済み件数が最少のキーワードから順に処理することで均等配分になり、
    # かつ各キーワードが上限文字数に最も近づくタイトルを選べる
    exhausted = set()
    while remaining and len(exhausted) < len(seasons):
        key = min(
            (k for k in seasons if k not in exhausted), key=lambda k: (counts[k], priority[k])
        )
        keyword = keywords[key]
        target = next(
            (
                t
                for t in remaining
                if keyword not in t['title']
                and len(t['title']) + separator_length + len(keyword) <= title_limit
            ),
            None,
        )
        if target is None:
            # このキーワードを付加できるタイトルはもう残っていない
            exhausted.add(key)
            continue

        remaining.remove(target)
        separator, rotation_index = _pick_separator(target['title'], rotation_index)
        target['title'] = f"{target['title']}{separator}{keyword}"
        counts[key] += 1

    applied = sum(counts.values())
    logger.info(f"季節・カラーキーワードを {applied} 件のタイトルに付加しました: {counts}")
