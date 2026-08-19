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


def _append_best_fit(
    remaining: list[dict[str, str]],
    keyword: str,
    avoid_words: Sequence[str],
    rotation_index: int,
    separator_length: int,
    title_limit: int,
) -> int | None:
    """収まる中で最も長いタイトルへ keyword を付加する（合体・単独共通の中核処理）。

    remaining は長い順である前提（next() が「収まる中で最も長い」タイトルを返す）。
    avoid_words のいずれかを含むタイトルは重複回避のため飛ばす。
    付加できたら対象を remaining から除き、更新後の rotation_index を返す。
    付加先が無ければ None を返す（remaining は変更しない）。
    """
    target = next(
        (
            t
            for t in remaining
            if all(word not in t['title'] for word in avoid_words)
            and len(t['title']) + separator_length + len(keyword) <= title_limit
        ),
        None,
    )
    if target is None:
        return None

    remaining.remove(target)
    separator, rotation_index = _pick_separator(target['title'], rotation_index)
    target['title'] = f"{target['title']}{separator}{keyword}"
    return rotation_index


def _apply_combo_keywords(
    remaining: list[dict[str, str]],
    seasons: Sequence[str],
    counts: dict[str, int],
    rotation_index: int,
    separator_length: int,
    title_limit: int,
) -> int:
    """季節×ブリーチなしの合体語を SEASON_COMBO_SLOTS 件を目安に付加する。

    - 季節（春〜冬）と bleach_free の両方が選択されているときのみ動く
    - 複数季節選択時は正規化順（config 定義順）にローテーションして配分する
    - 付加は季節側・bleach_free 側の両方の counts に計上する（未付与判定と整合させる）
    - 付加したタイトルは remaining から除くので、後続の単独配分には影響しない
    - 合体が収まる超短尺タイトルが無ければ目安件数未満で終わる（確率的達成でよい）

    Returns:
        更新後の rotation_index
    """
    combo_seasons = config.combo_season_keys(seasons)
    if not combo_seasons:
        return rotation_index

    bleach_word = config.SEASON_COLOR_CHOICES['bleach_free']
    applied = 0
    cycle = 0
    # 合体語長は全季節で同一だが、重複回避で特定季節だけ付加先が尽きることがあるため
    # break ではなく季節単位で管理し、残りの季節へ枠を回す
    exhausted: set[str] = set()
    while applied < config.SEASON_COMBO_SLOTS and len(exhausted) < len(combo_seasons):
        key = combo_seasons[cycle % len(combo_seasons)]
        cycle += 1
        if key in exhausted:
            continue
        result = _append_best_fit(
            remaining,
            config.season_combo_keyword(key),
            (config.SEASON_COLOR_CHOICES[key], bleach_word),
            rotation_index,
            separator_length,
            title_limit,
        )
        if result is None:
            exhausted.add(key)
            continue

        rotation_index = result
        counts[key] += 1
        counts['bleach_free'] += 1
        applied += 1

    if applied:
        logger.info(f"季節×ブリーチなしの合体キーワードを {applied} 件のタイトルに付加しました")
    return rotation_index


def apply_season_keywords(templates: list[dict[str, str]], seasons: Sequence[str]) -> list[str]:
    """選択された季節・カラーキーワードをタイトルへ付加する（テンプレートを直接書き換える）

    - SEASON_APPEND_THRESHOLD 文字未満のタイトルのみが対象
    - 付加後に上限文字数を超える場合は付加しない
    - 季節と bleach_free の両方が選択されている場合は、合体語
      （「秋カラー×ブリーチなしカラー」など）を SEASON_COMBO_SLOTS 件を目安に先に付加し、
      合体語入りテンプレートをリストの先頭へ並べ替える（それ以外の相対順は保つ）
    - 複数選択時は対象タイトルへ均等に配分する
    - 各キーワードには、収まる範囲で最も長いタイトル＝上限文字数に最も近づくものを割り当てる
    - 区切り記号はタイトルが使っている記号に合わせ、記号がなければローテーションする

    呼び出し側は渡したリストの中身が書き換わることを前提にしている。

    Returns:
        どのタイトルにも含まれなかったキーワードのキー（'spring' など）のリスト。
        付加できなくても既にタイトルに含まれていれば未付与とは数えない
        （検索キーワード自体が「春カラー」などの場合）。選択がなければ空。
    """
    if not seasons:
        return []
    if not templates:
        # 実運用では generator が空テンプレートで先に GenerationError を投げるため
        # 到達しないが、防御的に「全キーワード未付与」として返す
        return list(dict.fromkeys(seasons))

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

    # 合体付加を単独付加より先に行う。合体の対象（超短尺タイトル）は単独付加でも
    # 消費されうるため、先取りしないと合体枠が単独語に奪われてしまう
    rotation_index = _apply_combo_keywords(
        remaining, seasons, counts, rotation_index, separator_length, title_limit
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
        result = _append_best_fit(
            remaining, keyword, (keyword,), rotation_index, separator_length, title_limit
        )
        if result is None:
            # このキーワードを付加できるタイトルはもう残っていない
            exhausted.add(key)
            continue

        rotation_index = result
        counts[key] += 1

    # 合体語入りテンプレートを生成結果の先頭に出す（ユーザー要望）。
    # 安定ソートなので、先頭グループ内・それ以外の相対順はどちらも変わらない
    combo_words = [config.season_combo_keyword(k) for k in config.combo_season_keys(seasons)]
    if combo_words:
        templates.sort(key=lambda t: not any(word in t.get('title', '') for word in combo_words))

    applied = sum(counts.values())
    logger.info(f"季節・カラーキーワードを {applied} 件のタイトルに付加しました: {counts}")

    # 付加件数 0 でも、重複回避でスキップしただけでタイトルに既に含まれている場合は
    # 「未付与」ではない（バナーの文言が事実と矛盾してしまう）
    unapplied = [
        key
        for key in seasons
        if counts[key] == 0 and not any(keywords[key] in t.get('title', '') for t in templates)
    ]
    if unapplied:
        # 自動リトライはしない（generator.py の要求数未達 warning と同じ方針）。
        # 付加できなかった事実は運用で追えるようログに残し、呼び出し側へ返す。
        logger.warning(
            f"選択された季節・カラーのうち付加先が見つからなかったものがあります: {unapplied}"
        )
    return unapplied
