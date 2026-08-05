// ページ内の主要な要素をここで一度だけ引く。
//
// 何をここに載せるかの規約:
//   1. el に載せるのは「index.html に最初から存在し、生存期間がページと同じ」要素だけ。
//   2. 動的に生成した要素は、それを生成したモジュールが自分のスコープで引く。
//      （template-card.js が card.querySelector で閉じる、toast.js が自分で作った
//        .toast を引く、など）これは違反ではない。
//   3. 同じセレクタ文字列が 2 つ以上のモジュールに現れたら、必ずここへ寄せる。

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

// 上のセレクタと index.html は文字列一致でしか結ばれていない。id や class を
// 変えると静かに null になり、実行時に初めて TypeError で落ちる。
// 起動時に一度だけ検査して、取り違えをその場で分かるようにする。
// （null を ?. で握りつぶす方針にすると「何も起きない」不具合になり原因を追えない）
const missingElements = Object.entries(el)
    .filter(([, node]) => node === null || (node instanceof NodeList && node.length === 0))
    .map(([key]) => key);
if (missingElements.length > 0) {
    console.error('[dom] index.html に見つからない要素:', missingElements.join(', '));
}

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
