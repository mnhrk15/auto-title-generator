// アイコンの SVG。実体は base.html の <svg class="icon-sprite"> にあり、ここでは参照だけを作る。
// テンプレート側の同じ役割は _macros.html の icon() マクロ。
//
// アイコンは意味のあるもの（copy / check / close / alert）だけに使う。
// ラベルや見出しを飾る目的では付けない。

/** @param {'copy'|'check'|'close'|'alert'} name */
export function icon(name) {
    return `<svg class="icon" aria-hidden="true" focusable="false"><use href="#icon-${name}"></use></svg>`;
}
