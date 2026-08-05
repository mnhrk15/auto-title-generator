// ページ内の主要な要素をここで一度だけ引く。
// セレクタ文字列を各モジュールに散らさないための単一の出入口。

export const el = {
    generateBtn: document.getElementById('generate-button'),
    keywordInput: document.getElementById('keyword'),
    loading: document.getElementById('loading'),
    loadingMessage: document.querySelector('.loading-message'),

    progressBar: document.querySelector('.progress-bar'),
    progressFill: document.getElementById('progress-fill'),
    progressStep: document.getElementById('progress-step'),
    progressPercent: document.getElementById('progress-percent'),
    stepIndicators: document.querySelectorAll('.step-indicator'),

    // グローバルエラー表示。id で引くのは、特集キーワード欄にも
    // .error-message というクラス名の要素があり、DOM 順に依存してしまうため。
    errorSection: document.getElementById('error-message'),
    errorText: document.querySelector('#error-message .error-text'),

    results: document.getElementById('results'),
    templateContainer: document.getElementById('template-container'),
    templatesLoading: document.getElementById('templates-loading'),
    templateCardTemplate: document.querySelector('#template-card'),

    exportAllBtn: document.getElementById('export-all'),
    copyAllBtn: document.getElementById('copy-all'),

    pagination: document.querySelector('.pagination'),
    prevPageBtn: document.getElementById('prev-page'),
    nextPageBtn: document.getElementById('next-page'),
    paginationNumbers: document.getElementById('pagination-numbers'),

    copiedToast: document.getElementById('copied-toast'),

    genderRadios: document.querySelectorAll('input[name="gender"]'),
    seasonCheckboxes: document.querySelectorAll('input[name="season"]'),
    seasonSelection: document.getElementById('season-selection'),
    mensNotice: document.getElementById('mens-title-notice'),
    featuredContainer: document.getElementById('featured-keywords-container'),
};

/** 現在選択されている性別を返す */
export function getSelectedGender() {
    const checked = document.querySelector('input[name="gender"]:checked');
    return checked ? checked.value : 'ladies';
}

/** チェックされている季節・カラーの value 配列を返す */
export function getSelectedSeasons() {
    return Array.from(document.querySelectorAll('input[name="season"]:checked'))
        .map((cb) => cb.value);
}
