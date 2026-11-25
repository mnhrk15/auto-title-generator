// 「生成」ボタンのフロー。

import { ApiError, TIMEOUT_GENERATE_MS, requestJson } from './api.js';
import { el, getSelectedGender, getSelectedSeasons } from './dom.js';
import {
    completeProgress, resetProgress, startProgressSimulation, stopProgressSimulation,
} from './progress.js';
import { hideError, hideLoading, hideResults, showError, showLoading, showResults } from './status.js';
import { showToast } from './toast.js';
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

function notifySuccess(data) {
    const featuredName = data.featured_keyword_info?.name;

    if (data.is_featured && featuredName) {
        showToast({
            message: `特集「${featuredName}」のテンプレートを${data.templates.length}件生成しました`,
            variant: 'featured',
            duration: 4000,
        });
    } else if (data.is_featured) {
        showToast({ message: '特集キーワードのテンプレートを生成しました', variant: 'success' });
    } else {
        showToast({ message: 'テンプレートを生成しました', variant: 'success' });
    }
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
    const keyword = el.keywordInput.value.trim();
    const gender = getSelectedGender();
    const seasons = getSelectedSeasons();

    if (!keyword) {
        showError('キーワードを入力してください。');
        el.keywordInput.focus();
        return;
    }

    showLoading();
    hideError();
    hideResults();
    resetProgress();
    startProgressSimulation();

    el.generateBtn.disabled = true;
    el.generateBtn.textContent = BUTTON_BUSY_TEXT;

    try {
        // model は送らない。UI にモデル選択が無く、サーバー側にデフォルトがあるため。
        const data = await requestJson('/api/generate', {
            method: 'POST',
            body: { keyword, gender, seasons },
            timeoutMs: TIMEOUT_GENERATE_MS,
        });

        completeProgress();
        notifySuccess(data);
        updateMensNotice(gender);
        updateSeasonUnappliedNotice(data.unapplied_season_keywords);
        displayTemplates(data.templates);
        showResults();
        el.results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
        console.error('テンプレート生成中にエラー:', error);

        // エラー時はシミュレーションのみ停止（一瞬「100% 完了」と見える不具合を回避）
        stopProgressSimulation();

        if (error instanceof ApiError) {
            handleApiError(error);
        } else {
            showError(NETWORK_ERROR_MESSAGES.app);
        }
    } finally {
        hideLoading();
        el.generateBtn.disabled = false;
        el.generateBtn.textContent = BUTTON_IDLE_TEXT;
        stopProgressSimulation();
    }
}

export function initGenerate() {
    el.generateBtn.addEventListener('click', generate);

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
