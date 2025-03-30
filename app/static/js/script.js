document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-button');
    const keywordInput = document.getElementById('keyword');
    const loadingSpinner = document.querySelector('.loading');
    const progressFill = document.querySelector('.progress-fill');
    const progressStep = document.querySelector('.progress-step');
    const progressPercent = document.querySelector('.progress-percent');
    const loadingMessage = document.querySelector('.loading-message');
    const errorMessage = document.querySelector('.error-message');
    const errorText = document.querySelector('.error-text');
    const resultsSection = document.querySelector('.results-section');
    const templateContainer = document.querySelector('.template-container');
    const exportCsvBtn = document.getElementById('exportCsv');
    const exportTxtBtn = document.getElementById('exportTxt');
    
    // プログレスバーの状態
    let progressState = {
        currentStep: 0,
        steps: [
            { name: 'スクレイピング中...', percent: 25 },
            { name: 'タイトル解析中...', percent: 50 },
            { name: 'テンプレート生成中...', percent: 75 },
            { name: '完了', percent: 100 }
        ],
        interval: null
    };
    
    // 初期アニメーション
    animateElements();
    
    // フォーカス処理
    keywordInput.focus();

    // キーボードショートカット
    document.addEventListener('keydown', (e) => {
        // Enterキーで生成
        if (e.key === 'Enter' && document.activeElement === keywordInput) {
            generateBtn.click();
        }
    });
    
    // テンプレート生成
    generateBtn.addEventListener('click', async () => {
        const keyword = keywordInput.value.trim();
        const gender = document.querySelector('input[name="gender"]:checked').value;
        
        if (!keyword) {
            showError('キーワードを入力してください。');
            keywordInput.focus();
            return;
        }
        
        showLoading();
        hideError();
        hideResults();
        
        // プログレスバーをリセット
        resetProgress();
        
        // プログレスシミュレーションを開始
        startProgressSimulation();
        
        // ボタンを無効化
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 生成中...';
        
        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ keyword, gender })
            });
            
            const data = await response.json();
            
            // プログレスを100%に設定
            completeProgress();
            
            if (data.success) {
                displayTemplates(data.templates);
                // 成功時のフィードバック
                showSuccessToast('テンプレートを生成しました');
            } else {
                showError(data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            showError('テンプレートの生成中にエラーが発生しました。');
            // エラー時もプログレスを完了に設定
            completeProgress();
        } finally {
            hideLoading();
            // ボタンを再度有効化
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-magic"></i> 生成';
            // プログレスシミュレーションを停止
            stopProgressSimulation();
        }
    });
    
    // プログレスバーをリセット
    function resetProgress() {
        progressState.currentStep = 0;
        updateProgressUI(0, progressState.steps[0].name);
    }
    
    // プログレスシミュレーションを開始
    function startProgressSimulation() {
        // 既存のインターバルをクリア
        if (progressState.interval) {
            clearInterval(progressState.interval);
        }
        
        // 最初のステップを表示
        updateProgressUI(
            progressState.steps[0].percent,
            progressState.steps[0].name
        );
        
        // 次のステップに進む前の遅延時間（ミリ秒）
        const stepDelay = 2000;
        
        // 進行状況のシミュレーション
        progressState.interval = setInterval(() => {
            // 次のステップに進む
            progressState.currentStep = Math.min(
                progressState.currentStep + 1,
                progressState.steps.length - 1
            );
            
            // UIを更新
            const step = progressState.steps[progressState.currentStep];
            updateProgressUI(step.percent, step.name);
            
            // 最終ステップに達したら停止
            if (progressState.currentStep >= progressState.steps.length - 1) {
                stopProgressSimulation();
            }
        }, stepDelay);
    }
    
    // プログレスシミュレーションを停止
    function stopProgressSimulation() {
        if (progressState.interval) {
            clearInterval(progressState.interval);
            progressState.interval = null;
        }
    }
    
    // プログレスを100%に設定
    function completeProgress() {
        stopProgressSimulation();
        updateProgressUI(100, '完了');
    }
    
    // プログレスUIを更新
    function updateProgressUI(percent, stepName) {
        // パーセントを更新
        progressFill.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        
        // ステップ名を更新
        progressStep.textContent = stepName;
        
        // ロード中のメッセージを更新
        loadingMessage.textContent = `テンプレートを${stepName}`;
    }
    
    // 成功トースト表示
    function showSuccessToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast success-toast';
        toast.innerHTML = `
            <i class="fas fa-check-circle"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(toast);
        
        // アニメーション
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // 3秒後に消える
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }
    
    // テンプレートカードの表示
    function displayTemplates(templates) {
        templateContainer.innerHTML = '';
        
        // 遅延表示でアニメーション効果を高める
        templates.forEach((template, index) => {
            setTimeout(() => {
                const card = createTemplateCard(template);
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                templateContainer.appendChild(card);
                
                // フェードイン
                setTimeout(() => {
                    card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 50);
            }, index * 100);
        });
        
        showResults();
        
        // スクロール
        setTimeout(() => {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 300);
    }
    
    // 初期要素のアニメーション
    function animateElements() {
        const elements = [
            document.querySelector('.guide'),
            document.querySelector('.search-section')
        ];
        
        elements.forEach((el, index) => {
            if (el) {
                el.style.opacity = '0';
                el.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                    el.style.opacity = '1';
                    el.style.transform = 'translateY(0)';
                }, 300 + index * 200);
            }
        });
    }
    
    // テンプレートカードの作成
    function createTemplateCard(template) {
        const templateContent = document.getElementById('template-card').content.cloneNode(true);
        const card = templateContent.querySelector('.template-card');
        
        // 各フィールドに値を設定
        const titleInput = card.querySelector('.title');
        const menuInput = card.querySelector('.menu');
        const commentInput = card.querySelector('.comment');
        const hashtagInput = card.querySelector('.hashtag');
        
        titleInput.value = template.title;
        menuInput.value = template.menu;
        commentInput.value = template.comment;
        hashtagInput.value = template.hashtag;
        
        // テキストコンテンツを適切に表示
        ensureTextVisibility(titleInput);
        ensureTextVisibility(menuInput);
        ensureTextVisibility(commentInput);
        ensureTextVisibility(hashtagInput);
        
        // 文字数カウントの初期設定
        updateCharCount(titleInput, card.querySelector('.title-count'), 30);
        updateCharCount(menuInput, card.querySelector('.menu-count'), 50);
        updateCharCount(commentInput, card.querySelector('.comment-count'), 120);
        updateHashtagCount(hashtagInput, card.querySelector('.hashtag-count'));
        
        // 文字数カウントのイベントリスナー
        titleInput.addEventListener('input', () => {
            updateCharCount(titleInput, card.querySelector('.title-count'), 30);
            autoResizeTextarea(titleInput);
        });
        
        menuInput.addEventListener('input', () => {
            updateCharCount(menuInput, card.querySelector('.menu-count'), 50);
            autoResizeTextarea(menuInput);
        });
        
        commentInput.addEventListener('input', () => {
            updateCharCount(commentInput, card.querySelector('.comment-count'), 120);
            autoResizeTextarea(commentInput);
        });
        
        hashtagInput.addEventListener('input', () => {
            updateHashtagCount(hashtagInput, card.querySelector('.hashtag-count'));
            autoResizeTextarea(hashtagInput);
        });
        
        // 自動リサイズ
        autoResizeTextarea(titleInput);
        autoResizeTextarea(menuInput);
        autoResizeTextarea(commentInput);
        autoResizeTextarea(hashtagInput);
        
        // コピーボタンの設定
        const copyBtn = card.querySelector('.copy-btn');
        copyBtn.addEventListener('click', () => {
            const content = [
                titleInput.value,
                menuInput.value,
                commentInput.value,
                hashtagInput.value
            ].join('\n\n');
            
            navigator.clipboard.writeText(content).then(() => {
                const originalText = copyBtn.textContent;
                copyBtn.innerHTML = '<i class="fas fa-check"></i> コピー完了！';
                copyBtn.disabled = true;
                copyBtn.classList.add('copied');
                
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i> コピー';
                    copyBtn.disabled = false;
                    copyBtn.classList.remove('copied');
                }, 2000);
            }).catch(err => {
                console.error('コピーに失敗しました:', err);
                showError('テキストのコピーに失敗しました。');
            });
        });
        
        return card;
    }
    
    // テキストが見切れないように調整
    function ensureTextVisibility(textarea) {
        // テキストの内容が長い場合、スクロールバーを表示
        if (textarea.scrollHeight > textarea.clientHeight) {
            textarea.style.overflowY = 'auto';
        } else {
            textarea.style.overflowY = 'hidden';
        }
    }
    
    // テキストエリアの自動リサイズ
    function autoResizeTextarea(textarea) {
        // 最小の高さを保存
        const minHeight = parseInt(window.getComputedStyle(textarea).getPropertyValue('min-height'));
        
        // 一時的に高さをリセットしてスクロールの高さを測定
        textarea.style.height = 'auto';
        
        // スクロールの高さと最小の高さを比較して大きい方を設定
        const newHeight = Math.max(textarea.scrollHeight, minHeight);
        textarea.style.height = newHeight + 'px';
        
        // スクロールが必要かどうかを判断
        ensureTextVisibility(textarea);
    }
    
    // CSVエクスポート
    exportCsvBtn.addEventListener('click', () => {
        const templates = getTemplatesFromCards();
        if (templates.length === 0) {
            showError('エクスポートするテンプレートがありません。');
            return;
        }
        
        const csv = [
            ['category', 'title', 'menu', 'comment', 'hashtag'].join(','),
            ...templates.map(t => [
                'Generated',
                `"${t.title.replace(/"/g, '""')}"`,
                `"${t.menu.replace(/"/g, '""')}"`,
                `"${t.comment.replace(/"/g, '""')}"`,
                `"${t.hashtag.replace(/"/g, '""')}"`
            ].join(','))
        ].join('\n');
        
        downloadFile(csv, 'templates.csv', 'text/csv');
        showSuccessToast('CSVファイルをダウンロードしました');
    });
    
    // TXTエクスポート
    exportTxtBtn.addEventListener('click', () => {
        const templates = getTemplatesFromCards();
        if (templates.length === 0) {
            showError('エクスポートするテンプレートがありません。');
            return;
        }
        
        const txt = templates.map(t => 
            `【タイトル】\n${t.title}\n\n` +
            `【メニュー】\n${t.menu}\n\n` +
            `【コメント】\n${t.comment}\n\n` +
            `【ハッシュタグ】\n${t.hashtag}\n\n` +
            '='.repeat(40) + '\n'
        ).join('\n');
        
        downloadFile(txt, 'templates.txt', 'text/plain');
        showSuccessToast('テキストファイルをダウンロードしました');
    });
    
    // 表示中のカードからテンプレート情報を取得
    function getTemplatesFromCards() {
        const cards = templateContainer.querySelectorAll('.template-card');
        return Array.from(cards).map(card => ({
            title: card.querySelector('.title').value,
            menu: card.querySelector('.menu').value,
            comment: card.querySelector('.comment').value,
            hashtag: card.querySelector('.hashtag').value
        }));
    }
    
    // ファイルダウンロード
    function downloadFile(content, filename, type) {
        const blob = new Blob([content], { type });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }
    
    // ユーティリティ関数
    function showLoading() {
        loadingSpinner.classList.remove('hidden');
    }
    
    function hideLoading() {
        loadingSpinner.classList.add('hidden');
    }
    
    function showError(message) {
        errorText.textContent = message;
        errorMessage.classList.remove('hidden');
        
        // エラーが表示されている場合はスクロール
        errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // 3秒後に自動的に非表示
        setTimeout(() => {
            hideError();
        }, 5000);
    }
    
    function hideError() {
        errorMessage.classList.add('hidden');
    }
    
    function showResults() {
        resultsSection.classList.remove('hidden');
    }
    
    function hideResults() {
        resultsSection.classList.add('hidden');
    }
    
    // 文字数カウントの更新
    function updateCharCount(input, countElement, maxLength) {
        const length = input.value.length;
        countElement.textContent = `${length}/${maxLength}`;
        
        // 文字数に応じてスタイルを変更
        countElement.classList.remove('warning', 'error');
        if (length >= maxLength) {
            countElement.classList.add('error');
        } else if (length >= maxLength * 0.8) {
            countElement.classList.add('warning');
        }
    }
    
    // ハッシュタグの文字数カウント
    function updateHashtagCount(input, countElement) {
        const hashtags = input.value.split(',').map(tag => tag.trim()).filter(tag => tag);
        const longTags = hashtags.filter(tag => tag.length > 20);
        
        if (longTags.length > 0) {
            countElement.textContent = `${longTags.length}個のタグが20文字を超えています`;
            countElement.classList.add('error');
        } else {
            countElement.textContent = `${hashtags.length}個のタグ`;
            countElement.classList.remove('warning', 'error');
        }
    }
    
    // リサイズイベントでテキストエリアのサイズを再調整
    window.addEventListener('resize', () => {
        const textareas = document.querySelectorAll('textarea');
        textareas.forEach(textarea => {
            autoResizeTextarea(textarea);
        });
    });
    
    // トーストのスタイルを追加
    addToastStyles();
    
    function addToastStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .toast {
                position: fixed;
                bottom: 20px;
                right: 20px;
                padding: 12px 20px;
                background-color: white;
                color: var(--text-color);
                border-radius: var(--border-radius-md);
                box-shadow: var(--shadow-md);
                display: flex;
                align-items: center;
                gap: 10px;
                z-index: 1000;
                transform: translateY(100px);
                opacity: 0;
                transition: transform 0.3s ease, opacity 0.3s ease;
            }
            
            .toast.show {
                transform: translateY(0);
                opacity: 1;
            }
            
            .toast.success-toast i {
                color: var(--success-color);
                font-size: 18px;
            }
            
            .copy-btn.copied {
                background-color: var(--success-color);
            }
            
            @media (max-width: 768px) {
                .toast {
                    left: 20px;
                    right: 20px;
                    bottom: 20px;
                    text-align: center;
                    justify-content: center;
                }
            }
        `;
        document.head.appendChild(style);
    }
}); 