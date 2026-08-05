// 生成結果のエクスポート（CSV / テキスト）と全件コピー。

import { copyToClipboard } from './clipboard.js';
import { el } from './dom.js';
import { showError } from './status.js';
import { showToast } from './toast.js';
import { formatTemplateForExport, hashtagToText } from './template-format.js';
import { getAllTemplates } from './template-list.js';

function toCsv(templates) {
    const quote = (value) => `"${String(value).replace(/"/g, '""')}"`;
    const header = ['タイトル', 'メニュー', 'コメント', 'ハッシュタグ'].join(',');
    const rows = templates.map((t) => [
        quote(t.title), quote(t.menu), quote(t.comment), quote(hashtagToText(t.hashtag)),
    ].join(','));

    // Excel で開いた際に文字化けしないよう BOM を付ける
    return `﻿${header}\n${rows.join('\n')}`;
}

function downloadFile(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

function buildDialog() {
    const dialog = document.createElement('div');
    dialog.className = 'export-dialog';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-label', 'エクスポート形式を選択');
    dialog.innerHTML = `
        <div class="export-dialog-content">
            <div class="export-dialog-header">
                <h3>エクスポート形式を選択</h3>
                <button type="button" class="close-btn" aria-label="閉じる">
                    <i class="fas fa-times" aria-hidden="true"></i>
                </button>
            </div>
            <div class="export-dialog-body">
                <button type="button" class="export-option" data-format="csv">
                    <i class="fas fa-file-csv" aria-hidden="true"></i>
                    <span>CSV形式</span>
                </button>
                <button type="button" class="export-option" data-format="txt">
                    <i class="fas fa-file-alt" aria-hidden="true"></i>
                    <span>テキスト形式</span>
                </button>
            </div>
        </div>
    `;
    return dialog;
}

function openExportDialog(templates) {
    const dialog = buildDialog();
    document.body.appendChild(dialog);

    const onKeydown = (event) => {
        if (event.key === 'Escape') closeDialog();
    };

    function closeDialog() {
        document.removeEventListener('keydown', onKeydown);
        dialog.remove();
    }
    document.addEventListener('keydown', onKeydown);

    dialog.querySelector('[data-format="csv"]').addEventListener('click', () => {
        downloadFile(toCsv(templates), 'hair_templates.csv', 'text/csv;charset=utf-8');
        showToast({ message: 'CSVファイルをダウンロードしました', icon: 'fa-check-circle', variant: 'success' });
        closeDialog();
    });

    dialog.querySelector('[data-format="txt"]').addEventListener('click', () => {
        const text = templates.map(formatTemplateForExport).join('\n');
        downloadFile(text, 'hair_templates.txt', 'text/plain');
        showToast({ message: 'テキストファイルをダウンロードしました', icon: 'fa-check-circle', variant: 'success' });
        closeDialog();
    });

    dialog.querySelector('.close-btn').addEventListener('click', closeDialog);
    dialog.addEventListener('click', (event) => {
        if (event.target === dialog) closeDialog();
    });
}

export function initExport() {
    el.exportAllBtn.addEventListener('click', () => {
        const templates = getAllTemplates();
        if (!templates.length) {
            showError('エクスポートするテンプレートがありません');
            return;
        }
        openExportDialog(templates);
    });

    el.copyAllBtn.addEventListener('click', async () => {
        const templates = getAllTemplates();
        if (!templates.length) {
            showError('コピーするテンプレートがありません');
            return;
        }

        await copyToClipboard(
            templates.map(formatTemplateForExport).join('\n'),
            'すべてのテンプレート',
        );
    });
}
