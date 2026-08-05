// エントリポイント。
//
// <script type="module"> は暗黙的に defer されるため、
// DOM の構築完了後・DOMContentLoaded の前に実行される。
// したがって DOMContentLoaded で包む必要はない。

import { autoResizeTextarea } from './template-card.js';
import { initExport } from './export.js';
import { initFeaturedKeywords } from './featured-keywords.js';
import { initFormControls } from './form-controls.js';
import { initGenerate } from './generate.js';
import { initPagination } from './template-list.js';

const RESIZE_DEBOUNCE_MS = 150;

/** 画面幅が変わると textarea の折り返しが変わるので高さを取り直す */
function initResizeHandler() {
    let timer = null;
    window.addEventListener('resize', () => {
        clearTimeout(timer);
        timer = setTimeout(() => {
            // 結果が出ていないときは走らせない（毎回の全走査は強制リフローを招く）
            document.querySelectorAll('.template-card textarea').forEach(autoResizeTextarea);
        }, RESIZE_DEBOUNCE_MS);
    });
}

initFormControls();
initFeaturedKeywords();
initGenerate();
initPagination();
initExport();
initResizeHandler();
