// トーストと通知の生成。
//
// このアプリのトーストは2種類ある:
//   1. showToast()     … 画面右下にスタックする .toast（成功・エラー・情報）
//   2. showCopyToast() … 画面下中央のピル型 #copied-toast（コピー操作の確認だけ）
// 役割も見た目も別物なので統合していない。
//
// 以前は右下トーストの生成コードが8箇所にコピペされ、クラス名も8種類に散っていた。

const SHOW_DELAY_MS = 10;      // 付与→トランジション開始のための1フレーム待ち
const REMOVE_DELAY_MS = 300;   // フェードアウト完了を待つ時間（CSS の transition と対応）
const COPY_TOAST_DURATION_MS = 2000;

/**
 * 画面右下にトーストを表示する。
 *
 * @param {object}  options
 * @param {string}  options.message  本文
 * @param {string} [options.title]   見出し（省略時は本文のみ）
 * @param {string}  options.icon     Font Awesome のクラス（例: 'fa-check-circle'）
 * @param {string} [options.variant] 'success' | 'info' | 'error' | 'primary' | 'accent' | 'featured'
 * @param {number} [options.duration] 表示時間(ms)
 */
export function showToast({ message, title = '', icon = 'fa-info-circle', variant = 'info', duration = 3000 }) {
    // 同時に複数出さない（元々 success 系だけが行っていた挙動を全 variant に統一）
    document.querySelector('.toast')?.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast--${variant}`;
    toast.setAttribute('role', variant === 'error' ? 'alert' : 'status');
    toast.setAttribute('aria-live', variant === 'error' ? 'assertive' : 'polite');

    const iconEl = document.createElement('i');
    iconEl.className = `fas ${icon}`;
    iconEl.setAttribute('aria-hidden', 'true');
    toast.appendChild(iconEl);

    // textContent で入れる（サーバー由来の文字列を innerHTML に流さない）
    if (title) {
        const body = document.createElement('div');
        const titleEl = document.createElement('div');
        titleEl.className = 'toast-title';
        titleEl.textContent = title;
        const messageEl = document.createElement('div');
        messageEl.className = 'toast-message';
        messageEl.textContent = message;
        body.append(titleEl, messageEl);
        toast.appendChild(body);
    } else {
        const span = document.createElement('span');
        span.textContent = message;
        toast.appendChild(span);
    }

    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), SHOW_DELAY_MS);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), REMOVE_DELAY_MS);
    }, duration);

    return toast;
}

/** コピー操作の確認（画面下中央のピル） */
export function showCopyToast(fieldName = '') {
    const toastEl = document.getElementById('copied-toast');
    if (!toastEl) return;

    toastEl.textContent = fieldName
        ? `${fieldName}をクリップボードにコピーしました`
        : 'クリップボードにコピーしました';
    toastEl.classList.add('show');

    clearTimeout(showCopyToast._timer);
    showCopyToast._timer = setTimeout(() => toastEl.classList.remove('show'), COPY_TOAST_DURATION_MS);
}

/**
 * 操作ボタンを持つ通知バナーを表示する。
 *
 * @param {object}   options
 * @param {string}   options.title
 * @param {string}   options.body
 * @param {string}  [options.className]  追加クラス
 * @param {Array}   [options.actions]    [{label, icon, onClick}]
 * @param {number}  [options.duration]
 */
export function showNotification({ title, body, className = '', actions = [], duration = 10000 }) {
    const notification = document.createElement('div');
    notification.className = `featured-fallback-notification ${className}`.trim();
    notification.setAttribute('role', 'status');
    notification.setAttribute('aria-live', 'polite');

    const content = document.createElement('div');
    content.className = 'notification-content';

    const icon = document.createElement('i');
    icon.className = 'fas fa-info-circle';
    icon.setAttribute('aria-hidden', 'true');

    const text = document.createElement('div');
    text.className = 'notification-text';
    const strong = document.createElement('strong');
    strong.textContent = title;
    const p = document.createElement('p');
    p.textContent = body;
    text.append(strong, p);

    content.append(icon, text);

    const close = () => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), REMOVE_DELAY_MS);
    };

    const actionsWrapper = document.createElement('div');
    actionsWrapper.className = 'notification-actions';

    // インライン onclick は使わない。ES モジュールのスコープからは
    // グローバルに公開していない関数を参照できず ReferenceError になるため。
    actions.forEach(({ label, icon: actionIcon, onClick }) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'notification-action-btn';
        const i = document.createElement('i');
        i.className = `fas ${actionIcon}`;
        i.setAttribute('aria-hidden', 'true');
        button.append(i, document.createTextNode(label));
        button.addEventListener('click', () => {
            onClick?.();
            close();
        });
        actionsWrapper.appendChild(button);
    });

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'notification-close';
    closeButton.setAttribute('aria-label', '通知を閉じる');
    const closeIcon = document.createElement('i');
    closeIcon.className = 'fas fa-times';
    closeIcon.setAttribute('aria-hidden', 'true');
    closeButton.appendChild(closeIcon);
    closeButton.addEventListener('click', close);
    actionsWrapper.appendChild(closeButton);

    content.appendChild(actionsWrapper);
    notification.appendChild(content);
    document.body.appendChild(notification);

    setTimeout(() => notification.classList.add('show'), 100);
    setTimeout(close, duration);

    return notification;
}
