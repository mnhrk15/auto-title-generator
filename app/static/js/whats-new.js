// UI 刷新のお知らせ（index.html の #whats-new-dialog）。
//
// ブラウザごとに 1 回だけ開く。「見た」ことだけを localStorage に残す。
// 次に別の大きな変更を知らせるときは、STORAGE_KEY の日付部分を変えれば全員にもう一度出る。
//
// localStorage が使えない環境（ブロックされている等）では、毎回出てしつこくなるのを避けて出さない。

import { el } from './dom.js';

const STORAGE_KEY = 'whatsNewSeen:2026-11-ui';

function hasSeen() {
    try {
        return window.localStorage.getItem(STORAGE_KEY) !== null;
    } catch {
        return true;
    }
}

function markSeen() {
    try {
        window.localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    } catch {
        // 保存できなくても閉じる操作は妨げない
    }
}

export function initWhatsNew() {
    const dialog = el.whatsNewDialog;
    if (!dialog || typeof dialog.showModal !== 'function' || hasSeen()) return;

    // ボタン・✕・Escape のどれで閉じても close イベントが来る
    dialog.addEventListener('close', () => {
        markSeen();
        // 閉じるとブラウザが元のフォーカス（キーワード欄）へ戻す。スマホではその瞬間に
        // ソフトキーボードが開いてしまうので、指で操作する端末ではフォーカスを外しておく
        if (window.matchMedia('(pointer: coarse)').matches) {
            document.activeElement?.blur();
        }
    }, { once: true });

    // 背景（ダイアログの外側）を押したときも閉じる。押し始めと離した位置の両方が背景のときに限る。
    // 文字の選択などで、片方だけが背景になったドラッグでは閉じない
    let pressedOnBackdrop = false;
    let releasedOnBackdrop = false;
    dialog.addEventListener('pointerdown', (event) => {
        pressedOnBackdrop = event.target === dialog;
    });
    dialog.addEventListener('pointerup', (event) => {
        releasedOnBackdrop = event.target === dialog;
    });
    dialog.addEventListener('click', (event) => {
        if (pressedOnBackdrop && releasedOnBackdrop && event.target === dialog) dialog.close();
    });
    dialog.showModal();
}
