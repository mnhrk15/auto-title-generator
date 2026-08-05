// 特集キーワードの取得・表示・選択。

import { ApiError, TIMEOUT_FEATURED_KEYWORDS_MS, requestJson } from './api.js';
import { el, getSelectedGender } from './dom.js';
import { showNotification, showToast } from './toast.js';

const GENDER_LABELS = {
    ladies: 'レディース',
    mens: 'メンズ',
};

// 特集キーワードの選択で性別を自動変更した直後は、その change を
// 「ユーザーの手動変更」と誤判定しないための猶予
const AUTO_SELECTION_GRACE_MS = 1000;
// これ以上経っていれば、性別はユーザーが自分で選んだとみなす
const MANUAL_SELECTION_THRESHOLD_MS = 3000;

const ERROR_MESSAGES = {
    timeout: '特集キーワードの読み込みがタイムアウトしました',
    network: 'ネットワークエラーが発生しました',
    server: 'サーバーで問題が発生しています',
    app: '特集キーワードの読み込みに失敗しました',
};

const RETRY_ERROR_MESSAGES = {
    timeout: '再試行がタイムアウトしました',
    network: 'ネットワークエラーが継続しています',
    server: 'サーバーの問題が継続しています',
    app: '再試行に失敗しました',
};

class FeaturedKeywordsManager {
    constructor() {
        this.keywords = [];
        this.selectedKeyword = null;
        this.lastSelectionTime = null;
        // サーバーが返した降格メッセージ。描画で container を空にするため、
        // 読み込み時点では保持だけして renderFeaturedKeywords() の最後に表示する
        this.fallbackMessage = null;
        this.container = el.featuredContainer;
        this.keywordInput = el.keywordInput;
        this.genderRadios = el.genderRadios;
    }

    async init() {
        try {
            this.renderLoadingState();
            await this.loadFeaturedKeywords();
            this.renderFeaturedKeywords();
            this.setupGenderChangeListeners();
        } catch (error) {
            console.error('特集キーワードの初期化に失敗:', error);
            const kind = error instanceof ApiError ? error.kind : 'app';
            // サーバー起因（503）も一過性のことがあり、再読み込み以外に復帰手段が
            // なくなってしまうため、種別によらず再試行ボタンを出す
            this.renderErrorState(ERROR_MESSAGES[kind], true);
            this.showFallbackNotification();
        }
    }

    setupGenderChangeListeners() {
        this.genderRadios.forEach((radio) => {
            radio.addEventListener('change', (event) => {
                // 特集キーワード選択による自動変更なら何もしない
                if (this.lastSelectionTime
                    && Date.now() - this.lastSelectionTime < AUTO_SELECTION_GRACE_MS) {
                    return;
                }

                this.reloadKeywordsForGender(event.target.value);

                if (this.selectedKeyword) {
                    this.clearSelection();
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

    async loadFeaturedKeywords(gender = null) {
        const target = gender || getSelectedGender();
        const data = await requestJson(`/api/featured-keywords?gender=${target}`, {
            timeoutMs: TIMEOUT_FEATURED_KEYWORDS_MS,
        });

        this.keywords = Array.isArray(data.keywords) ? data.keywords : [];

        // 機能が降格している場合（設定なし・読み込み失敗）はメッセージだけ出して継続する。
        // ここで DOM に入れても直後の描画で消えてしまうので、保持だけしておく。
        this.fallbackMessage = data.message || null;
    }

    renderFeaturedKeywords() {
        if (!this.container) return;

        this.container.innerHTML = '';

        if (this.keywords.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'featured-keywords-empty';
            empty.innerHTML = '<i class="fas fa-info-circle" aria-hidden="true"></i>';
            empty.append('現在、特集キーワードはありません');
            this.container.appendChild(empty);
        } else {
            this.keywords.forEach((keyword) => {
                this.container.appendChild(this.createKeywordButton(keyword));
            });
        }

        if (this.fallbackMessage) {
            this.showFallbackMessage(this.fallbackMessage);
            this.fallbackMessage = null;
        }
    }

    createKeywordButton(keyword) {
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
            button.disabled = true;   // 連続クリック防止
            try {
                this.selectFeaturedKeyword(keyword);
            } catch (error) {
                console.error('特集キーワード選択エラー:', error);
                showToast({
                    message: 'キーワードの選択に失敗しました',
                    icon: 'fa-exclamation-triangle',
                    variant: 'error',
                    duration: 2500,
                });
            } finally {
                setTimeout(() => { button.disabled = false; }, 500);
            }
        });

        return button;
    }

    selectFeaturedKeyword(keyword) {
        // 同じキーワードを再度押したら選択解除
        if (this.selectedKeyword && this.selectedKeyword.keyword === keyword.keyword) {
            this.deselectFeaturedKeyword();
            return;
        }

        this.clearSelection();

        if (this.keywordInput) {
            this.keywordInput.value = keyword.keyword;
            this.keywordInput.focus();
            this.keywordInput.dispatchEvent(new Event('input', { bubbles: true }));
        }

        this.selectGender(keyword.gender);
        this.updateButtonState(keyword);

        this.selectedKeyword = keyword;
        this.lastSelectionTime = Date.now();
    }

    deselectFeaturedKeyword() {
        if (this.selectedKeyword) {
            showToast({
                message: `特集キーワード「${this.selectedKeyword.name}」の選択を解除しました`,
                icon: 'fa-times-circle',
                variant: 'info',
                duration: 2000,
            });
        }

        if (this.keywordInput) {
            this.keywordInput.value = '';
            this.keywordInput.focus();
            this.keywordInput.dispatchEvent(new Event('input', { bubbles: true }));
        }

        this.clearSelection();
    }

    selectGender(gender) {
        const currentGender = getSelectedGender();
        if (currentGender === gender) return;

        // ユーザーが自分で選んだ設定を黙って上書きしない
        if (this.wasGenderManuallySelected()) {
            const message = `現在の性別設定「${GENDER_LABELS[currentGender]}」を`
                + `「${GENDER_LABELS[gender]}」に変更しますか？`;
            if (!window.confirm(message)) return;
        }

        this.genderRadios.forEach((radio) => {
            radio.checked = radio.value === gender;
            if (radio.checked) {
                radio.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });

        showToast({
            message: `性別を「${GENDER_LABELS[gender]}」に設定しました`,
            icon: gender === 'ladies' ? 'fa-female' : 'fa-male',
            variant: 'primary',
            duration: 1500,
        });
    }

    wasGenderManuallySelected() {
        if (!this.lastSelectionTime) return true;
        return Date.now() - this.lastSelectionTime > MANUAL_SELECTION_THRESHOLD_MS;
    }

    updateButtonState(selectedKeyword) {
        this.container.querySelectorAll('.featured-keyword-btn').forEach((button) => {
            // 表示名ではなく data 属性で同定する（表示名を変えても壊れない）
            const isActive = button.dataset.keyword === selectedKeyword.keyword;
            button.classList.toggle('active', isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
    }

    async reloadKeywordsForGender(gender) {
        try {
            this.renderLoadingState();
            this.clearSelection();
            await this.loadFeaturedKeywords(gender);
            this.renderFeaturedKeywords();
        } catch (error) {
            console.error('特集キーワードの再読み込みに失敗:', error);
            this.renderErrorState('特集キーワードの更新に失敗しました', true);
        }
    }

    clearSelection() {
        this.container?.querySelectorAll('.featured-keyword-btn').forEach((button) => {
            button.classList.remove('active');
            button.setAttribute('aria-pressed', 'false');
        });
        this.selectedKeyword = null;
        this.lastSelectionTime = null;
    }

    renderLoadingState() {
        if (!this.container) return;
        this.container.innerHTML = `
            <div class="featured-keywords-loading">
                <i class="fas fa-spinner fa-spin" aria-hidden="true"></i>
                <span>特集キーワードを読み込み中...</span>
            </div>
        `;
    }

    renderErrorState(message, showRetryButton = true) {
        if (!this.container) return;

        this.container.innerHTML = '';

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

        if (showRetryButton) {
            const retry = document.createElement('button');
            retry.type = 'button';
            retry.className = 'featured-keywords-retry-btn';
            retry.innerHTML = '<i class="fas fa-redo" aria-hidden="true"></i>';
            retry.append('再試行');
            // インライン onclick はモジュールスコープの変数を参照できず動かないため
            // addEventListener で結線する
            retry.addEventListener('click', () => this.retry());
            wrapper.appendChild(retry);
        }

        this.container.appendChild(wrapper);
    }

    showFallbackMessage(message) {
        if (!this.container) return;

        const warning = document.createElement('div');
        warning.className = 'featured-keywords-warning';
        const icon = document.createElement('i');
        icon.className = 'fas fa-info-circle';
        icon.setAttribute('aria-hidden', 'true');
        const span = document.createElement('span');
        span.textContent = message;
        warning.append(icon, span);

        this.container.insertBefore(warning, this.container.firstChild);
        setTimeout(() => warning.remove(), 5000);
    }

    showFallbackNotification() {
        showNotification({
            title: '特集キーワード機能が利用できません',
            body: '通常のテンプレート生成機能は引き続きご利用いただけます。',
        });
    }

    async retry() {
        try {
            this.renderLoadingState();
            // 押した手応えを出すために少し待つ
            await new Promise((resolve) => { setTimeout(resolve, 500); });

            await this.loadFeaturedKeywords();
            this.renderFeaturedKeywords();

            showToast({
                message: '特集キーワードを正常に読み込みました',
                icon: 'fa-check-circle',
                variant: 'success',
            });
        } catch (error) {
            console.error('特集キーワードの再試行に失敗:', error);
            const kind = error instanceof ApiError ? error.kind : 'app';
            this.renderErrorState(RETRY_ERROR_MESSAGES[kind], true);
        }
    }
}

export const featuredKeywords = new FeaturedKeywordsManager();

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
            onClick: () => featuredKeywords.clearSelection(),
        }],
    });
}

export function initFeaturedKeywords() {
    featuredKeywords.init();

    // 入力欄を直接編集したら特集キーワードの選択状態を解除する
    el.keywordInput.addEventListener('input', () => {
        if (!featuredKeywords.selectedKeyword) return;
        if (el.keywordInput.value.trim() !== featuredKeywords.selectedKeyword.keyword) {
            featuredKeywords.clearSelection();
        }
    });
}
