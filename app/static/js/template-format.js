// テンプレートのテキスト整形。
//
// カード内のコピーとエクスポートで同じ形式を使う。
// 以前は template-card.js と export.js に別々の実装があり、
// 片方だけ直すと出力がずれる状態だった。

const SEPARATOR = '='.repeat(40);

/** ハッシュタグは配列で来ることも、textarea 由来の文字列のこともある */
export function hashtagToText(hashtag) {
    return Array.isArray(hashtag) ? hashtag.join(', ') : (hashtag || '');
}

/** 【タイトル】〜【ハッシュタグ】の4ブロック */
export function formatTemplateFields({ title, menu, comment, hashtag }) {
    return [
        `【タイトル】\n${title}`,
        `【メニュー】\n${menu}`,
        `【コメント】\n${comment}`,
        `【ハッシュタグ】\n${hashtagToText(hashtag)}`,
    ].join('\n\n');
}

/** 通し番号ヘッダと区切り線を付けた、エクスポート1件ぶん */
export function formatTemplateForExport(template, index) {
    return [
        `■ テンプレート ${index + 1}`,
        formatTemplateFields(template),
        SEPARATOR,
    ].join('\n\n');
}
