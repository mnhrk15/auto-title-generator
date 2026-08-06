// 性別・季節カラーの選択状態に応じた表示制御と、初期アニメーション。

import { el, getSelectedGender } from './dom.js';

/** 選択中の性別オプションを強調する */
export function updateGenderSelectionStyles() {
    document.querySelectorAll('.gender-option-wrapper').forEach((wrapper) => {
        const radio = wrapper.querySelector('input[type="radio"]');
        const option = wrapper.querySelector('.gender-option');
        option.classList.toggle('gender-option-active', radio.checked);
        option.classList.toggle('gender-option-inactive', !radio.checked);
    });
}

/** チェック中の季節・カラーを強調する */
export function updateSeasonSelectionStyles() {
    document.querySelectorAll('.season-option').forEach((option) => {
        const checkbox = option.querySelector('input[type="checkbox"]');
        option.classList.toggle('season-option-active', checkbox.checked);
    });
}

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
    updateSeasonSelectionStyles();
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

/** 初期表示時のフェードイン */
function animateElements() {
    const target = document.querySelector('.search-section');
    if (!target) return;

    target.style.opacity = '0';
    target.style.transform = 'translateY(20px)';
    setTimeout(() => {
        target.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        target.style.opacity = '1';
        target.style.transform = 'translateY(0)';
    }, 300);
}

export function initFormControls() {
    updateGenderSelectionStyles();
    updateSeasonVisibility();

    el.genderRadios.forEach((radio) => {
        radio.addEventListener('change', () => {
            updateGenderSelectionStyles();
            updateSeasonVisibility();
        });
    });

    el.seasonCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener('change', updateSeasonSelectionStyles);
    });

    animateElements();
    el.keywordInput.focus();
}
