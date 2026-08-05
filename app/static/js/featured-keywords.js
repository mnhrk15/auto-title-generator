// 特集キーワードの取得・表示・選択。
//
// 「性別の変更がユーザー操作なのか、特集キーワード選択に伴う自動変更なのか」を
// 区別する必要がある。以前は Date.now() のしきい値で推測しており、
// 判定が実際の因果と一致していなかった（初回選択でボタンが active にならない、
// 性別に触れていないのに確認ダイアログが出る）。フラグで明示的に表す。

import { TIMEOUT_FEATURED_KEYWORDS_MS, errorKind, requestJson } from './api.js';
import { el, getSelectedGender } from './dom.js';
import { showNotification, showToast } from './toast.js';

const GENDER_LABELS = {
    ladies: 'レディース',
    mens: 'メンズ',
};

const RETRY_FEEDBACK_DELAY_MS = 500;   // 再試行ボタンを押した手応えのための待ち
const BUTTON_LOCK_MS = 500;            // 連続クリック防止
const WARNING_DURATION_MS = 5000;

const ERROR_MESSAGES = {
    timeout: '特集キーワードの読み込みがタイムアウトしました',
    network: 'ネットワークエラーが発生しました',
    server: 'サーバーで問題が発生しています',
    app: '特集キーワードの読み込みに失敗しました',
};

const RELOAD_ERROR_MESSAGES = {
    timeout: '特集キーワードの更新がタイムアウトしました',
    network: 'ネットワークエラーが発生しました',
    server: 'サーバーで問題が発生しています',
    app: '特集キーワードの更新に失敗しました',
};

const RETRY_ERROR_MESSAGES = {
    timeout: '再試行がタイムアウトしました',
    network: 'ネットワークエラーが継続しています',
    server: 'サーバーの問題が継続しています',
    app: '再試行に失敗しました',
};

const state = {
    keywords: [],
    selectedKeyword: null,
    // サーバーが返した降格メッセージ。描画で container を空にするため、
    // 読み込み時点では保持だけして renderFeaturedKeywords() の最後に表示する
    fallbackMessage: null,
    // 特集キーワード選択に伴って性別を書き換えている最中か。
    // dispatchEvent は同期なので、このフラグの寿命は同一コールスタックに閉じる。
    isApplyingGender: false,
    // ユーザーが自分で性別ラジオを操作したか。
    // 「選択の解除」とは別概念なので clearSelection() ではリセットしない。
    genderTouchedByUser: false,
};

/** 現在選択されている特集キーワード（未選択なら null） */
export function getSelectedKeyword() {
    return state.selectedKeyword;
}

// ---------------------------------------------------------------- 読み込み

async function loadFeaturedKeywords(gender = null) {
    const target = gender || getSelectedGender();
    const data = await requestJson(`/api/featured-keywords?gender=${target}`, {
        timeoutMs: TIMEOUT_FEATURED_KEYWORDS_MS,
    });

    state.keywords = Array.isArray(data.keywords) ? data.keywords : [];

    // 機能が降格している場合（設定なし・読み込み失敗）はメッセージだけ出して継続する。
    // ここで DOM に入れても直後の描画で消えてしまうので、保持だけしておく。
    state.fallbackMessage = data.message || null;
}

/**
 * 読み込み → 描画。失敗したらエラー状態を描く。
 *
 * @returns {Promise<boolean>} 成功したか
 */
async function loadAndRender(gender, errorMessages) {
    try {
        renderLoadingState();
        await loadFeaturedKeywords(gender);
        renderFeaturedKeywords();
        return true;
    } catch (error) {
        console.error('特集キーワードの読み込みに失敗:', error);
        // サーバー起因（503）も一過性のことがあり、再読み込み以外に復帰手段が
        // なくなってしまうため、種別によらず再試行ボタンを出す
        renderErrorState(errorMessages[errorKind(error)] ?? errorMessages.app);
        return false;
    }
}

async function retry() {
    renderLoadingState();
    // 押した手応えを出すために少し待つ
    await new Promise((resolve) => { setTimeout(resolve, RETRY_FEEDBACK_DELAY_MS); });

    if (await loadAndRender(null, RETRY_ERROR_MESSAGES)) {
        showToast({
            message: '特集キーワードを正常に読み込みました',
            icon: 'fa-check-circle',
            variant: 'success',
        });
    }
}

// ---------------------------------------------------------------- 描画

function renderLoadingState() {
    el.featuredContainer.innerHTML = `
        <div class="featured-keywords-loading">
            <i class="fas fa-spinner fa-spin" aria-hidden="true"></i>
            <span>特集キーワードを読み込み中...</span>
        </div>
    `;
}

function renderFeaturedKeywords() {
    const container = el.featuredContainer;
    container.innerHTML = '';

    if (state.keywords.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'featured-keywords-empty';
        empty.innerHTML = '<i class="fas fa-info-circle" aria-hidden="true"></i>';
        empty.append('現在、特集キーワードはありません');
        container.appendChild(empty);
    } else {
        state.keywords.forEach((keyword) => {
            container.appendChild(createKeywordButton(keyword));
        });
    }

    if (state.fallbackMessage) {
        showFallbackMessage(state.fallbackMessage);
        state.fallbackMessage = null;
    }
}

function createKeywordButton(keyword) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'featured-keyword-btn';
    button.dataset.keyword = keyword.keyword;
    button.dataset.name = keyword.name;
    button.dataset.gender = keyword.gender;
    button.setAttribute('aria-pressed', 'false');

    const icon = document.createElement('i');
    icon.className = 'fas fa-star';
    icon.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span');
    // JSON 由来の文字列なので textContent で入れる
    label.textContent = keyword.name;
    button.append(icon, label);

    button.addEventListener('click', () => {
        button.disabled = true;
        try {
            selectFeaturedKeyword(keyword);
        } catch (error) {
            console.error('特集キーワード選択エラー:', error);
            showToast({
                message: 'キーワードの選択に失敗しました',
                icon: 'fa-exclamation-triangle',
                variant: 'error',
                duration: 2500,
            });
        } finally {
            setTimeout(() => { button.disabled = false; }, BUTTON_LOCK_MS);
        }
    });

    return button;
}

function renderErrorState(message) {
    const container = el.featuredContainer;
    container.innerHTML = '';

    const wrapper = document.createElement('div');
    wrapper.className = 'featured-keywords-error';

    const content = document.createElement('div');
    content.className = 'error-content';
    const icon = document.createElement('i');
    icon.className = 'fas fa-exclamation-triangle';
    icon.setAttribute('aria-hidden', 'true');
    const text = document.createElement('span');
    // グローバルエラー用の .error-message とクラス名が衝突していたため改名
    text.className = 'featured-keywords-error-text';
    text.textContent = message;
    content.append(icon, text);
    wrapper.appendChild(content);

    const retryButton = document.createElement('button');
    retryButton.type = 'button';
    retryButton.className = 'featured-keywords-retry-btn';
    retryButton.innerHTML = '<i class="fas fa-redo" aria-hidden="true"></i>';
    retryButton.append('再試行');
    // インライン onclick はモジュールスコープの変数を参照できず動かないため
    // addEventListener で結線する
    retryButton.addEventListener('click', retry);
    wrapper.appendChild(retryButton);

    container.appendChild(wrapper);
}

function showFallbackMessage(message) {
    const warning = document.createElement('div');
    warning.className = 'featured-keywords-warning';
    const icon = document.createElement('i');
    icon.className = 'fas fa-info-circle';
    icon.setAttribute('aria-hidden', 'true');
    const span = document.createElement('span');
    span.textContent = message;
    warning.append(icon, span);

    el.featuredContainer.insertBefore(warning, el.featuredContainer.firstChild);
    setTimeout(() => warning.remove(), WARNING_DURATION_MS);
}

// ---------------------------------------------------------------- 選択

function selectFeaturedKeyword(keyword) {
    // 同じキーワードを再度押したら選択解除
    if (state.selectedKeyword && state.selectedKeyword.keyword === keyword.keyword) {
        deselectFeaturedKeyword();
        return;
    }

    clearSelection();

    // 性別の書き換えは入力欄の反映より先に行う。書き換えが一覧の再読み込みを
    // 起こすため、後続の updateButtonState が対象ボタンを見失わないようにする。
    if (!applyGender(keyword.gender)) return;

    el.keywordInput.value = keyword.keyword;
    el.keywordInput.focus();
    el.keywordInput.dispatchEvent(new Event('input', { bubbles: true }));

    state.selectedKeyword = keyword;
    updateButtonState(keyword);
}

function deselectFeaturedKeyword() {
    if (state.selectedKeyword) {
        showToast({
            message: `特集キーワード「${state.selectedKeyword.name}」の選択を解除しました`,
            icon: 'fa-times-circle',
            variant: 'info',
            duration: 2000,
        });
    }

    el.keywordInput.value = '';
    el.keywordInput.focus();
    el.keywordInput.dispatchEvent(new Event('input', { bubbles: true }));

    clearSelection();
}

/**
 * 性別ラジオを書き換える。
 *
 * @returns {boolean} 書き換えた（または既にその性別だった）か。
 *                    ユーザーが確認ダイアログで拒否した場合だけ false。
 */
function applyGender(gender) {
    if (getSelectedGender() === gender) return true;

    // ユーザーが自分で選んだ設定を黙って上書きしない
    if (state.genderTouchedByUser) {
        const message = `現在の性別設定「${GENDER_LABELS[getSelectedGender()]}」を`
            + `「${GENDER_LABELS[gender]}」に変更しますか？`;
        if (!window.confirm(message)) return false;
    }

    // dispatchEvent は同期なので、change ハンドラはこの try の中で走り切る。
    state.isApplyingGender = true;
    try {
        el.genderRadios.forEach((radio) => {
            radio.checked = radio.value === gender;
            if (radio.checked) {
                radio.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    } finally {
        state.isApplyingGender = false;
    }

    showToast({
        message: `性別を「${GENDER_LABELS[gender]}」に設定しました`,
        icon: gender === 'ladies' ? 'fa-female' : 'fa-male',
        variant: 'primary',
        duration: 1500,
    });
    return true;
}

function updateButtonState(selectedKeyword) {
    el.featuredContainer.querySelectorAll('.featured-keyword-btn').forEach((button) => {
        // 表示名ではなく data 属性で同定する（表示名を変えても壊れない）
        const isActive = button.dataset.keyword === selectedKeyword.keyword;
        button.classList.toggle('active', isActive);
        button.setAttribute('aria-pressed', String(isActive));
    });
}

/** 特集キーワードの選択状態を解除する */
export function clearSelection() {
    el.featuredContainer.querySelectorAll('.featured-keyword-btn').forEach((button) => {
        button.classList.remove('active');
        button.setAttribute('aria-pressed', 'false');
    });
    state.selectedKeyword = null;
}

// ---------------------------------------------------------------- 通知

function showFallbackNotification() {
    showNotification({
        title: '特集キーワード機能が利用できません',
        body: '通常のテンプレート生成機能は引き続きご利用いただけます。',
    });
}

/** 特集キーワード関連のエラー時に、選択解除を促す通知を出す */
export function showFeaturedErrorFallbackNotification() {
    showNotification({
        title: '特集キーワード機能でエラーが発生しました',
        body: '特集キーワードの選択を解除して、通常のテンプレート生成をお試しください。',
        className: 'featured-error-fallback-notification',
        duration: 15000,
        actions: [{
            label: '選択を解除',
            icon: 'fa-times-circle',
            onClick: clearSelection,
        }],
    });
}

// ---------------------------------------------------------------- 初期化

function setupGenderChangeListeners() {
    el.genderRadios.forEach((radio) => {
        radio.addEventListener('change', (event) => {
            // 特集キーワード選択に伴う自動変更なら、ユーザー操作として扱わない
            if (state.isApplyingGender) return;

            state.genderTouchedByUser = true;

            // reloadKeywordsForGender は内部で同期的に clearSelection() するため、
            // 選択の有無は呼ぶ前に確定させる
            const hadSelection = Boolean(state.selectedKeyword);

            clearSelection();
            loadAndRender(event.target.value, RELOAD_ERROR_MESSAGES);

            if (hadSelection) {
                showToast({
                    message: `性別を手動で「${GENDER_LABELS[event.target.value]}」に変更しました`,
                    icon: 'fa-hand-pointer',
                    variant: 'accent',
                    duration: 2000,
                });
            }
        });
    });
}

export function initFeaturedKeywords() {
    // 読み込みの成否に関わらずリスナーを張る。以前は読み込み成功後に張っていたため、
    // 初回ロードが失敗すると性別を切り替えても一覧が更新されなくなっていた
    // （再試行で成功しても同じ）。
    setupGenderChangeListeners();

    // 入力欄を直接編集したら特集キーワードの選択状態を解除する
    el.keywordInput.addEventListener('input', () => {
        if (!state.selectedKeyword) return;
        if (el.keywordInput.value.trim() !== state.selectedKeyword.keyword) {
            clearSelection();
        }
    });

    loadAndRender(null, ERROR_MESSAGES).then((ok) => {
        if (!ok) showFallbackNotification();
    });
}
