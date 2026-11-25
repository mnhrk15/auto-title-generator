// 生成結果の一覧表示。
//
// allTemplates がテンプレートの唯一の出典。カード上での編集はここへ書き戻すので、
// エクスポートや全件コピーにも編集内容が反映される。
// 件数は 20 件前後なので、ページ送りはせずに全件を並べる。

import { el } from './dom.js';
import { createTemplateCard, initializeTextareas } from './template-card.js';

const state = {
    allTemplates: [],
};

/**
 * 全テンプレート（カード上の編集を反映済み）を返す。
 *
 * シャローコピーなので要素オブジェクト自体は共有される。目的は完全な不変性ではなく、
 * 呼び出し側の sort / splice が元データを壊すのを防ぐこと。
 */
export function getAllTemplates() {
    return [...state.allTemplates];
}

/** カード上の編集を元データへ書き戻す */
function updateTemplateField(index, field, value) {
    const template = state.allTemplates[index];
    if (!template) return;
    template[field] = value;
}

/**
 * 全件をカードにして描画する。
 * textarea の高さは、DOM に入っていて表示中でないと測れない。呼び出し側は先に結果欄を表示すること。
 */
export function displayTemplates(templates) {
    state.allTemplates = templates;

    const fragment = document.createDocumentFragment();
    templates.forEach((template, index) => {
        const card = createTemplateCard(template, index, updateTemplateField);
        // 届いた直後だけ、上から順に現れる動きを付ける（CSS の .is-entering と --i）
        card.classList.add('is-entering');
        card.style.setProperty('--i', String(index));
        card.addEventListener('animationend', () => card.classList.remove('is-entering'), { once: true });
        fragment.appendChild(card);
    });
    el.templateContainer.replaceChildren(fragment);
    initializeTextareas();
}
