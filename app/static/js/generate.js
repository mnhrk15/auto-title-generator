// 「生成」「再生成」のフロー。
//
// 生成中は前回の結果を薄く残して操作できないようにし、成功したら差し替える。
// 失敗・中止したら前回の結果をそのまま戻す。

import { ApiError, TIMEOUT_GENERATE_MS, requestJson } from './api.js';
import { el, getSelectedGender, getSelectedSeasons } from './dom.js';
import { startElapsedTimer, stopElapsedTimer } from './progress.js';
import {
    announce, hideError, hideLoading, setResultsBusy, showError, showLoading, showResults,
} from './status.js';
import { updateMensNotice, updateSeasonUnappliedNotice } from './form-controls.js';
import { displayTemplates } from './template-list.js';
import {
    clearSelection, getSelectedKeyword, showFeaturedErrorFallbackNotification,
} from './featured-keywords.js';

const NETWORK_ERROR_MESSAGES = {
    timeout: 'テンプレート生成がタイムアウトしました。もう一度お試しください。',
    network: 'ネットワークエラーが発生しました。インターネット接続を確認してください。',
    app: 'テンプレートの生成中にエラーが発生しました。',
};

const BUTTON_IDLE_TEXT = '生成';
const BUTTON_BUSY_TEXT = '生成中…';

// 実行中の生成を中止するための controller。null なら生成中ではない。
let activeController = null;

/** 結果見出しの件数と特集名 */
function updateResultsSummary(data) {
    const count = `${data.templates.length}件`;
    el.resultsCount.textContent = count;
    el.resultsActionsCount.textContent = count;

    const featuredName = data.featured_keyword_info?.name;
    el.resultsFeatured.textContent = featuredName ? `特集: ${featuredName}` : '特集キーワード';
    el.resultsFeatured.classList.toggle('hidden', !data.is_featured);
}

function setBusy(isBusy) {
    el.generateBtn.disabled = isBusy;
    el.generateBtn.textContent = isBusy ? BUTTON_BUSY_TEXT : BUTTON_IDLE_TEXT;
    setResultsBusy(isBusy);
}

/** サーバーが返したエラーコードに応じた案内を出す */
function handleApiError(error) {
    if (error.kind === 'server' || error.kind === 'app') {
        if (error.code === 'FEATURED_KEYWORDS_ERROR') {
            showError('特集キーワード機能でエラーが発生しましたが、通常のテンプレート生成を試行できます。');
            if (getSelectedKeyword()) {
                clearSelection();
                showFeaturedErrorFallbackNotification();
            }
            return;
        }
        // NO_RESULTS_FOUND / VALIDATION_ERROR / SCRAPING_ERROR などは
        // サーバーが用意した日本語メッセージをそのまま見せる
        showError(error.message);
        return;
    }

    showError(NETWORK_ERROR_MESSAGES[error.kind] || NETWORK_ERROR_MESSAGES.app);
}

async function generate() {
    if (activeController) return;

    const keyword = el.keywordInput.value.trim();
    const gender = getSelectedGender();
    const seasons = getSelectedSeasons();

    if (!keyword) {
        showError('キーワードを入力してください。');
        el.keywordInput.focus();
        return;
    }

    const controller = new AbortController();
    activeController = controller;

    // 結果欄の「再生成」から押された場合、結果欄は inert になってフォーカスが失われるので、
    // 待ち表示の「中止」へ移しておく
    const focusWasInResults = el.results.contains(document.activeElement);

    hideError();
    setBusy(true);
    showLoading();
    if (focusWasInResults) el.cancelBtn.focus();
    startElapsedTimer();
    announce('生成を開始しました');

    try {
        // model は送らない。UI にモデル選択が無く、サーバー側にデフォルトがあるため。
        const data = await requestJson('/api/generate', {
            method: 'POST',
            body: { keyword, gender, seasons },
            timeoutMs: TIMEOUT_GENERATE_MS,
            signal: controller.signal,
        });

        updateMensNotice(gender);
        updateSeasonUnappliedNotice(data.unapplied_season_keywords);
        updateResultsSummary(data);
        // 先に表示してから描画する。非表示（display: none）のままだと textarea の高さが測れず 0 になる
        setResultsBusy(false);
        showResults();
        displayTemplates(data.templates);
        announce(`${data.templates.length}件の結果を表示しました`);
        el.results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
        if (error instanceof ApiError && error.kind === 'cancelled') {
            // 自分で押した中止なので通知は出さず、前回の状態に戻すだけ
            announce('生成を中止しました');
            return;
        }

        console.error('テンプレート生成中にエラー:', error);
        announce('生成に失敗しました');
        if (error instanceof ApiError) {
            handleApiError(error);
        } else {
            showError(NETWORK_ERROR_MESSAGES.app);
        }
    } finally {
        activeController = null;
        stopElapsedTimer();
        // 「中止」にフォーカスがあったまま隠すと、フォーカスが body に落ちて見失う
        const focusWasInLoading = el.loading.contains(document.activeElement);
        hideLoading();
        setBusy(false);
        if (focusWasInLoading) el.generateBtn.focus({ preventScroll: true });
    }
}

/**
 * 生成を中止する。サーバー側の処理は止まらない（結果を受け取らずに捨てるだけ）。
 */
function cancelGeneration() {
    activeController?.abort();
}

export function initGenerate() {
    el.generateBtn.addEventListener('click', generate);
    el.cancelBtn.addEventListener('click', cancelGeneration);

    // 「再生成」は今の入力内容のまま生成し直す
    el.regenerateButtons.forEach((button) => {
        button.addEventListener('click', generate);
    });

    // 入力欄で Enter を押しても生成する。
    // 日本語入力の変換を確定する Enter では送信しない（isComposing、古い Safari 向けに keyCode 229）。
    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' || document.activeElement !== el.keywordInput) return;
        if (event.isComposing || event.keyCode === 229) return;
        el.generateBtn.click();
    });

    // エラー表示は自動で消さず、ユーザーが入力を直し始めた時点で消す
    el.keywordInput.addEventListener('input', hideError);
}
