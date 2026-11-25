// ローディング・エラー・結果セクションの表示制御。

import { el } from './dom.js';

/** 画面外にあるときだけ、最小限のスクロールで見える位置に出す */
function revealIfOffscreen(element) {
    const rect = element.getBoundingClientRect();
    if (rect.top < 0 || rect.bottom > window.innerHeight) {
        element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

export function showLoading() {
    el.loading.classList.remove('hidden');
    el.loading.setAttribute('aria-busy', 'true');
    // 結果欄の下の「再生成」から押されたときに、待ち表示が見えないままにならないようにする
    revealIfOffscreen(el.loading);
}

export function hideLoading() {
    el.loading.classList.add('hidden');
    el.loading.setAttribute('aria-busy', 'false');
}

/**
 * グローバルエラーを表示する。
 * 長い待ち時間のあとに出ることがあるので自動では消さない。
 * 次の生成開始時（generate.js）とキーワードの入力時に hideError() で消す。
 */
export function showError(message) {
    el.errorText.textContent = message;
    el.errorSection.classList.remove('hidden');
    el.errorSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

export function hideError() {
    el.errorSection.classList.add('hidden');
}

export function showResults() {
    el.results.classList.remove('hidden');
}

/**
 * 生成中は前回の結果を薄く残し、操作できないようにする。
 * 失敗・中止したら元に戻すので、隠さずに inert で止める。
 */
export function setResultsBusy(isBusy) {
    el.results.classList.toggle('is-busy', isBusy);
    el.results.inert = isBusy;
}

/**
 * 読み上げ用のお知らせ（画面には出さない）。秒数のような頻繁に変わる値は流さない。
 * 同じ文言を続けて入れても変化と見なされず読み上げられないので、一度空にしてから入れる。
 */
export function announce(message) {
    el.srStatus.textContent = '';
    requestAnimationFrame(() => {
        el.srStatus.textContent = message;
    });
}
