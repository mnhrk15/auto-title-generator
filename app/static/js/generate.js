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

const BUTTON_IDLE_HTML = '<i class="fas fa-magic" aria-hidden="true"></i> 生成';
const BUTTON_BUSY_HTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> 生成中...';

function notifySuccess(data) {
    const featuredName = data.featured_keyword_info?.name;

    if (data.is_featured && featuredName) {
        showToast({
            title: '特集対応テンプレート生成完了！',
            message: `「${featuredName}」の特集テンプレート ${data.templates.length}件を生成しました`,
            icon: 'fa-star',
            variant: 'featured',
            duration: 4000,
        });
    } else if (data.is_featured) {
        showToast({ message: '特集対応テンプレートを生成しました ⭐', icon: 'fa-check-circle', variant: 'success' });
    } else {
        showToast({ message: 'テンプレートを生成しました', icon: 'fa-check-circle', variant: 'success' });
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
    el.generateBtn.innerHTML = BUTTON_BUSY_HTML;

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

        if (getSelectedKeyword()) {
            setTimeout(showFeaturedErrorFallbackNotification, 2000);
        }
    } finally {
        hideLoading();
        el.generateBtn.disabled = false;
        el.generateBtn.innerHTML = BUTTON_IDLE_HTML;
        stopProgressSimulation();
    }
}

export function initGenerate() {
    el.generateBtn.addEventListener('click', generate);

    // 入力欄で Enter を押しても生成する
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && document.activeElement === el.keywordInput) {
            el.generateBtn.click();
        }
    });
}
