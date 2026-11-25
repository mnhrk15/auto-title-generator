// 性別・季節カラーの選択状態に応じた表示制御。
//
// 選択中の見た目は CSS の :has(input:checked) で付けるので、ここではクラスを付け外ししない。

import { el, getSelectedGender } from './dom.js';

/** メンズでは季節・カラー選択を非表示にする（選択済みの内容も解除する） */
export function updateSeasonVisibility() {
    if (!el.seasonSelection) return;

    const isMens = getSelectedGender() === 'mens';

    el.seasonSelection.classList.toggle('hidden', isMens);
    if (isMens) {
        el.seasonSelection.querySelectorAll('input[name="season"]').forEach((cb) => {
            cb.checked = false;
        });
    }
}

/** メンズ生成時のみ結果画面に注釈バナーを表示する */
export function updateMensNotice(gender) {
    if (!el.mensNotice) return;

    const isMens = gender === 'mens';
    el.mensNotice.classList.toggle('hidden', !isMens);
    if (!isMens) {
        const details = el.mensNotice.querySelector('details');
        if (details) details.open = false;
    }
}

/** 季節・カラーが1件も付与できなかったときの注釈バナーを更新する */
export function updateSeasonUnappliedNotice(keywords) {
    if (!el.seasonUnappliedNotice || !el.seasonUnappliedKeywords) return;

    const list = Array.isArray(keywords) ? keywords : [];
    el.seasonUnappliedKeywords.textContent = list.join('・');
    el.seasonUnappliedNotice.classList.toggle('hidden', list.length === 0);
}

export function initFormControls() {
    updateSeasonVisibility();

    el.genderRadios.forEach((radio) => {
        radio.addEventListener('change', updateSeasonVisibility);
    });

    el.keywordInput.focus();
}
