// テンプレートカード1枚の生成と、カード内の入力・コピー操作。

import { el } from './dom.js';
import { showError } from './status.js';
import { showCopyToast } from './toast.js';

const FIELD_LABELS = {
    title: 'タイトル',
    menu: 'メニュー',
    comment: 'コメント',
    hashtag: 'ハッシュタグ',
};

const HASHTAG_MAX_LENGTH = 20;
const COPY_FEEDBACK_MS = 1500;
const COPY_ALL_FEEDBACK_MS = 2000;

/** 文字数カウンターを更新する。上限は textarea 自身の maxlength を唯一の出典にする */
export function updateCharCount(textarea, countElement) {
    const length = textarea.value.length;
    const maxLength = textarea.maxLength;

    countElement.textContent = `${length}/${maxLength}`;
    countElement.classList.remove('warning', 'error');
    if (length >= maxLength) {
        countElement.classList.add('error');
    } else if (length >= maxLength * 0.8) {
        countElement.classList.add('warning');
    }
}

/** ハッシュタグは「タグ個数と各タグ長」で管理するので、全体文字数ではなく個数を出す */
export function updateHashtagCount(textarea, countElement) {
    const hashtags = textarea.value.split(',').map((tag) => tag.trim()).filter(Boolean);
    const longTags = hashtags.filter((tag) => tag.length > HASHTAG_MAX_LENGTH);

    if (longTags.length > 0) {
        countElement.textContent = `${longTags.length}個のタグが${HASHTAG_MAX_LENGTH}文字を超えています`;
        countElement.classList.add('error');
    } else {
        countElement.textContent = `${hashtags.length}個のタグ`;
        countElement.classList.remove('warning', 'error');
    }
}

/** フィールド種別に応じたカウンター更新 */
function refreshCount(textarea) {
    const counter = textarea.closest('.field')?.querySelector('.char-count');
    if (!counter) return;

    if (textarea.dataset.field === 'hashtag') {
        updateHashtagCount(textarea, counter);
    } else {
        updateCharCount(textarea, counter);
    }
}

/** 内容に合わせて textarea の高さを調整する */
export function autoResizeTextarea(textarea) {
    const minHeight = parseInt(window.getComputedStyle(textarea).getPropertyValue('min-height'), 10) || 0;

    textarea.style.height = 'auto';
    textarea.style.height = `${Math.max(textarea.scrollHeight, minHeight)}px`;

    // 収まらない場合だけスクロールバーを出す
    textarea.style.overflowY = textarea.scrollHeight > textarea.clientHeight ? 'auto' : 'hidden';
}

/** 表示中のすべての textarea を初期化する */
export function initializeTextareas() {
    document.querySelectorAll('.template-card textarea').forEach((textarea) => {
        autoResizeTextarea(textarea);
        refreshCount(textarea);
    });
}

function formatTemplateForCopy(values) {
    return [
        `【タイトル】\n${values.title}`,
        `【メニュー】\n${values.menu}`,
        `【コメント】\n${values.comment}`,
        `【ハッシュタグ】\n${values.hashtag}`,
    ].join('\n\n');
}

async function copyText(text, label) {
    try {
        await navigator.clipboard.writeText(text);
        showCopyToast(label);
        return true;
    } catch (error) {
        showError('コピーに失敗しました');
        console.error('コピーに失敗:', error);
        return false;
    }
}

/**
 * テンプレートカードを生成する。
 *
 * @param {object}   template     表示するテンプレート
 * @param {number}   globalIndex  全件中の通し番号（編集の書き戻しに使う）
 * @param {Function} onFieldChange (index, field, value) => void
 */
export function createTemplateCard(template, globalIndex, onFieldChange) {
    const fragment = el.templateCardTemplate.content.cloneNode(true);
    const card = fragment.querySelector('.template-card');

    const featuredIndicator = card.querySelector('.featured-indicator');
    const isFeatured = Boolean(template.is_featured);

    if (isFeatured) {
        featuredIndicator.classList.remove('hidden');
        card.classList.add('featured');

        const featuredKeywordName = template.featured_keyword_name;
        if (featuredKeywordName) {
            featuredIndicator.title = `特集キーワード: ${featuredKeywordName}`;
            const indicatorText = featuredIndicator.querySelector('span');
            if (indicatorText) {
                indicatorText.textContent = `特集対応 (${featuredKeywordName})`;
            }
        }
    } else {
        featuredIndicator.classList.add('hidden');
        card.classList.remove('featured');
    }

    const textareas = card.querySelectorAll('textarea[data-field]');
    textareas.forEach((textarea) => {
        const field = textarea.dataset.field;
        const value = template[field];
        textarea.value = Array.isArray(value) ? value.join(', ') : (value ?? '');

        refreshCount(textarea);
        autoResizeTextarea(textarea);

        textarea.addEventListener('input', () => {
            refreshCount(textarea);
            autoResizeTextarea(textarea);
            // 編集内容を元データへ書き戻す。これがないとページを移動した時点で
            // 編集が失われ、エクスポートにも反映されない。
            onFieldChange?.(globalIndex, field, textarea.value);
        });

        const container = textarea.closest('.textarea-container');
        textarea.addEventListener('focus', () => container?.classList.add('is-focused'));
        textarea.addEventListener('blur', () => container?.classList.remove('is-focused'));
    });

    // カードごとに表示タイミングを少しずらす
    card.style.animationDelay = `${(globalIndex % 6) * 0.05}s`;

    card.querySelectorAll('.field-copy-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const field = btn.dataset.field;
            const textarea = card.querySelector(`textarea[data-field="${field}"]`);
            if (!textarea) return;

            const originalIcon = btn.innerHTML;
            if (await copyText(textarea.value, FIELD_LABELS[field])) {
                btn.innerHTML = '<i class="fas fa-check" aria-hidden="true"></i>';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.innerHTML = originalIcon;
                    btn.classList.remove('copied');
                }, COPY_FEEDBACK_MS);
            }
        });
    });

    const copyBtn = card.querySelector('.copy-btn');
    copyBtn.addEventListener('click', async () => {
        const values = {};
        textareas.forEach((textarea) => { values[textarea.dataset.field] = textarea.value; });

        if (await copyText(formatTemplateForCopy(values), 'テンプレート全体')) {
            copyBtn.innerHTML = '<i class="fas fa-check" aria-hidden="true"></i> コピー完了';
            copyBtn.classList.add('copied');
            setTimeout(() => {
                copyBtn.innerHTML = '<i class="fas fa-copy" aria-hidden="true"></i> コピー';
                copyBtn.classList.remove('copied');
            }, COPY_ALL_FEEDBACK_MS);
        }
    });

    return card;
}
