// 生成結果の一覧表示とページネーション。
//
// allTemplates がテンプレートの唯一の出典。カード上での編集はここへ書き戻すので、
// ページを移動しても編集内容が残り、エクスポートにも全ページぶんが反映される。

import { el } from './dom.js';
import { createTemplateCard, initializeTextareas } from './template-card.js';
import { updateMensNotice } from './form-controls.js';

const ITEMS_PER_PAGE = 6;
const MAX_VISIBLE_PAGES = 5;
const RENDER_DELAY_MS = 300;   // スピナーを見せてUIの応答性を上げるための遅延

const state = {
    currentPage: 1,
    totalPages: 1,
    allTemplates: [],
};

/** 全テンプレート（カード上の編集を反映済み）を返す */
export function getAllTemplates() {
    return state.allTemplates;
}

/** カード上の編集を元データへ書き戻す */
function updateTemplateField(index, field, value) {
    const template = state.allTemplates[index];
    if (!template) return;
    template[field] = value;
}

function createPageButton(page, { label = String(page), isCurrent = false } = {}) {
    const button = document.createElement('button');
    button.type = 'button';
    button.classList.add('page-btn');
    button.textContent = label;
    if (isCurrent) button.classList.add('current-page');
    button.addEventListener('click', () => {
        if (page !== state.currentPage) displayTemplatesForPage(page);
    });
    return button;
}

function createEllipsis() {
    const ellipsis = document.createElement('span');
    ellipsis.classList.add('pagination-ellipsis');
    ellipsis.textContent = '...';
    return ellipsis;
}

function updatePaginationUI() {
    el.paginationNumbers.innerHTML = '';

    if (state.totalPages <= 1) {
        el.pagination.classList.add('hidden');
        return;
    }
    el.pagination.classList.remove('hidden');

    el.prevPageBtn.classList.toggle('disabled', state.currentPage <= 1);
    el.nextPageBtn.classList.toggle('disabled', state.currentPage >= state.totalPages);

    let startPage = Math.max(1, state.currentPage - Math.floor(MAX_VISIBLE_PAGES / 2));
    const endPage = Math.min(state.totalPages, startPage + MAX_VISIBLE_PAGES - 1);
    if (endPage - startPage + 1 < MAX_VISIBLE_PAGES && startPage > 1) {
        startPage = Math.max(1, endPage - MAX_VISIBLE_PAGES + 1);
    }

    if (startPage > 1) {
        el.paginationNumbers.appendChild(createPageButton(1));
        if (startPage > 2) el.paginationNumbers.appendChild(createEllipsis());
    }

    for (let i = startPage; i <= endPage; i += 1) {
        el.paginationNumbers.appendChild(
            createPageButton(i, { isCurrent: i === state.currentPage }),
        );
    }

    if (endPage < state.totalPages) {
        if (endPage < state.totalPages - 1) el.paginationNumbers.appendChild(createEllipsis());
        el.paginationNumbers.appendChild(createPageButton(state.totalPages));
    }
}

export function displayTemplatesForPage(page) {
    el.templatesLoading.classList.add('active');

    setTimeout(() => {
        el.templateContainer.innerHTML = '';

        const startIndex = (page - 1) * ITEMS_PER_PAGE;
        const pageTemplates = state.allTemplates.slice(startIndex, startIndex + ITEMS_PER_PAGE);

        pageTemplates.forEach((template, offset) => {
            el.templateContainer.appendChild(
                createTemplateCard(template, startIndex + offset, updateTemplateField),
            );
        });

        state.currentPage = page;
        updatePaginationUI();
        el.templatesLoading.classList.remove('active');
        initializeTextareas();
    }, RENDER_DELAY_MS);
}

export function displayTemplates(templates, gender = 'ladies') {
    state.allTemplates = templates;
    state.totalPages = Math.ceil(templates.length / ITEMS_PER_PAGE);
    state.currentPage = 1;

    updateMensNotice(gender);
    updatePaginationUI();
    displayTemplatesForPage(1);
}

export function initPagination() {
    el.prevPageBtn.addEventListener('click', () => {
        if (state.currentPage > 1) displayTemplatesForPage(state.currentPage - 1);
    });

    el.nextPageBtn.addEventListener('click', () => {
        if (state.currentPage < state.totalPages) displayTemplatesForPage(state.currentPage + 1);
    });
}
