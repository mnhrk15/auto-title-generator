// サーバー API 呼び出しの共通化。
//
// 呼び出し側が日本語メッセージの部分一致でエラー種別を判定していたのをやめ、
// ApiError.kind で分岐できるようにする。

export const TIMEOUT_FEATURED_KEYWORDS_MS = 10000;
export const TIMEOUT_GENERATE_MS = 120000;

/**
 * API 呼び出しの失敗。
 * kind: 'timeout' | 'network' | 'server' | 'app'
 *   - server: HTTP が 2xx でなかった（サーバー側の障害・入力エラー）
 *   - app:    HTTP は成功したが body の success が false だった
 */
export class ApiError extends Error {
    constructor(message, kind, { status = null, code = null } = {}) {
        super(message);
        this.name = 'ApiError';
        this.kind = kind;
        this.status = status;
        this.code = code;
    }
}

/**
 * JSON API を呼び出す。
 *
 * 非 2xx でも body を読んでから判定する。以前は body を読む前に throw していたため、
 * サーバーが返すエラーコード（NO_RESULTS_FOUND 等）に応じた案内が
 * 一度もユーザーに表示されていなかった。
 */
export async function requestJson(url, { method = 'GET', body = null, timeoutMs } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    let response;
    try {
        response = await fetch(url, {
            method,
            signal: controller.signal,
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
            body: body ? JSON.stringify(body) : undefined,
        });
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new ApiError('リクエストがタイムアウトしました', 'timeout');
        }
        if (error.name === 'TypeError') {
            throw new ApiError('ネットワークエラーが発生しました', 'network');
        }
        throw new ApiError(error.message, 'app');
    } finally {
        clearTimeout(timer);
    }

    // 非 2xx でも body を読む。サーバーは {success:false, error:{message, code}} を返す。
    let data = null;
    try {
        data = await response.json();
    } catch {
        data = null;
    }

    const message = data?.error?.message || data?.message;
    const code = data?.error?.code || null;

    if (!response.ok) {
        throw new ApiError(
            message || `サーバーエラー (${response.status})`,
            'server',
            { status: response.status, code },
        );
    }

    if (data && data.success === false) {
        throw new ApiError(message || '不明なエラーが発生しました。', 'app', { code });
    }

    if (!data || typeof data !== 'object') {
        throw new ApiError('無効なレスポンス形式です', 'app');
    }

    return data;
}
