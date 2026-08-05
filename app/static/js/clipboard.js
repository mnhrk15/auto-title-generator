// クリップボードへのコピーと、ボタン上での完了表示。

import { showCopyToast, showToast } from './toast.js';

const COPY_FEEDBACK_MS = 1500;

/**
 * クリップボードにコピーする。
 *
 * 失敗時は右下のエラートーストを出す。以前は status.js の showError を使っており、
 * コピーに失敗しただけでページが結果セクションの先頭までスクロールしていた。
 *
 * @param {string} text
 * @param {string} [label] 成功時のピルに出すフィールド名
 * @returns {Promise<boolean>} 成功したか
 */
export async function copyToClipboard(text, label = '') {
    try {
        await navigator.clipboard.writeText(text);
        showCopyToast(label);
        return true;
    } catch (error) {
        showToast({ message: 'コピーに失敗しました', icon: 'fa-times-circle', variant: 'error' });
        console.error('コピーに失敗:', error);
        return false;
    }
}

/**
 * コピー完了をボタン上で一時的に見せる。
 *
 * 連打ガードが必要な理由: ガードがないと、表示中（＝中身が「✓」）に再度押されたときに
 * その「✓」を復元対象として捕まえてしまい、元のアイコンに戻らなくなる。
 *
 * @param {HTMLElement} button
 * @param {string} doneHtml 完了時に差し込む HTML
 */
export function flashCopyFeedback(button, doneHtml) {
    if (button.classList.contains('copied')) return;

    const originalHtml = button.innerHTML;
    button.innerHTML = doneHtml;
    button.classList.add('copied');
    setTimeout(() => {
        button.innerHTML = originalHtml;
        button.classList.remove('copied');
    }, COPY_FEEDBACK_MS);
}
