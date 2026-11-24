// ローディング・エラー・結果セクションの表示制御。

import { el } from './dom.js';

export function showLoading() {
    el.loading.classList.remove('hidden');
    el.loading.setAttribute('aria-busy', 'true');
    el.loading.scrollIntoView({ behavior: 'smooth', block: 'start' });
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

export function hideResults() {
    el.results.classList.add('hidden');
}
