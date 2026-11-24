// 生成中の経過時間の表示。
//
// サーバーの実際の進み具合は取れないので、% や段階は出さない。以前は時間だけで % を進める
// 疑似進捗で、約 30 秒で 99% に達したあと 1 分以上止まって見えていた。
// 経過秒数と所要時間の目安（index.html の .loading-note）だけを正直に出す。

import { el } from './dom.js';

const TICK_MS = 1000;

let startedAt = 0;
let timer = null;

function render() {
    const seconds = Math.floor((Date.now() - startedAt) / TICK_MS);
    el.loadingElapsed.textContent = `${seconds}秒経過`;
}

export function startElapsedTimer() {
    stopElapsedTimer();
    startedAt = Date.now();
    render();
    timer = setInterval(render, TICK_MS);
}

export function stopElapsedTimer() {
    clearInterval(timer);
    timer = null;
}
