// テンプレートカード1枚の生成と、カード内の入力・コピー操作。

import { copyToClipboard, flashCopyFeedback } from './clipboard.js';
import { el } from './dom.js';
import { formatTemplateFields } from './template-format.js';

const FIELD_LABELS = {
    title: 'タイトル',
    menu: 'メニュー',
    comment: 'コメント',
    hashtag: 'ハッシュタグ',
};

// ハッシュタグの上限はタグ 1 個あたり。textarea 全体を制限する maxlength は使えないので、
// サーバーが data-max-length で渡す（出典は app/config.py の CHAR_LIMITS）。
const HASHTAG_MAX_LENGTH_FALLBACK = 20;

function hashtagMaxLength(textarea) {
    return Number(textarea.dataset.maxLength) || HASHTAG_MAX_LENGTH_FALLBACK;
}

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
    const maxLength = hashtagMaxLength(textarea);
    const hashtags = textarea.value.split(',').map((tag) => tag.trim()).filter(Boolean);
    const longTags = hashtags.filter((tag) => tag.length > maxLength);

    if (longTags.length > 0) {
        countElement.textContent = `${longTags.length}個のタグが${maxLength}文字を超えています`;
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

/** 表示中のすべてのカード内 textarea を返す */
function allCardTextareas() {
    return document.querySelectorAll('.template-card textarea');
}

/** 表示中のすべての textarea を初期化する */
export function initializeTextareas() {
    allCardTextareas().forEach((textarea) => {
        autoResizeTextarea(textarea);
        refreshCount(textarea);
    });
}

/** 表示中のすべての textarea の高さを取り直す（画面幅の変化時に使う） */
export function resizeAllTextareas() {
    allCardTextareas().forEach(autoResizeTextarea);
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

            if (await copyToClipboard(textarea.value, FIELD_LABELS[field])) {
                flashCopyFeedback(btn, '<i class="fas fa-check" aria-hidden="true"></i>');
            }
        });
    });

    const copyBtn = card.querySelector('.copy-btn');
    copyBtn.addEventListener('click', async () => {
        const values = {};
        textareas.forEach((textarea) => { values[textarea.dataset.field] = textarea.value; });

        if (await copyToClipboard(formatTemplateFields(values), 'テンプレート全体')) {
            flashCopyFeedback(copyBtn, '<i class="fas fa-check" aria-hidden="true"></i> コピー完了');
        }
    });

    return card;
}
