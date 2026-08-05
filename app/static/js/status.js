// ローディング・エラー・結果セクションの表示制御。

import { el } from './dom.js';

const ERROR_AUTO_HIDE_MS = 5000;

let errorHideTimer = null;

export function showLoading() {
    el.loading.classList.remove('hidden');
    el.loading.setAttribute('aria-busy', 'true');
    el.loading.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

export function hideLoading() {
    el.loading.classList.add('hidden');
    el.loading.setAttribute('aria-busy', 'false');
}

/** グローバルエラーを表示する（5秒後に自動的に非表示） */
export function showError(message) {
    el.errorText.textContent = message;
    el.errorSection.classList.remove('hidden');
    el.errorSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

    clearTimeout(errorHideTimer);
    errorHideTimer = setTimeout(hideError, ERROR_AUTO_HIDE_MS);
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
