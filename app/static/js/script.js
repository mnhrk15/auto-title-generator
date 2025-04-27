document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-button');
    const keywordInput = document.getElementById('keyword');
    const loadingSpinner = document.getElementById('loading');
    const progressFill = document.getElementById('progress-fill');
    const progressStep = document.getElementById('progress-step');
    const progressPercent = document.getElementById('progress-percent');
    const loadingMessage = document.querySelector('.loading-message');
    const errorMessage = document.querySelector('.error-message');
    const errorText = document.querySelector('.error-text');
    const resultsSection = document.getElementById('results');
    const templateContainer = document.getElementById('template-container');
    const exportAllBtn = document.getElementById('export-all');
    const copyAllBtn = document.getElementById('copy-all');
    const stepIndicators = document.querySelectorAll('.step-indicator');
    const genderRadios = document.querySelectorAll('input[name="gender"]');
    
    // ページネーションとトースト通知の要素
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    const paginationNumbers = document.getElementById('pagination-numbers');
    const copiedToast = document.getElementById('copied-toast');
    const templatesLoading = document.getElementById('templates-loading');
    
    // プログレスバーの状態
    let progressState = {
        currentStep: 0,
        steps: [
            { name: 'スクレイピング中...', percent: 20, duration: 5000 },
            { name: 'タイトル解析中...', percent: 40, duration: 3000 },
            { name: 'テンプレート生成中...', percent: 85, duration: 5000 },
            { name: '完了', percent: 100, duration: 500 }
        ],
        interval: null,
        subInterval: null
    };
    
    // ページネーション状態
    let paginationState = {
        currentPage: 1,
        itemsPerPage: 6,
        totalPages: 1,
        allTemplates: []
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
                showResults();
                // 成功時のフィードバック
                showSuccessToast('テンプレートを生成しました');
                // 結果表示領域までスクロール
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
        
        // すべてのステップインジケーターをリセット
        stepIndicators.forEach((indicator, index) => {
            indicator.classList.remove('active', 'completed');
        });
        
        // 最初のステップをアクティブにする
        stepIndicators[0].classList.add('active');
    }
    
    // プログレスシミュレーションを開始
    function startProgressSimulation() {
        // 既存のインターバルをクリア
        if (progressState.interval) {
            clearInterval(progressState.interval);
        }
        if (progressState.subInterval) {
            clearInterval(progressState.subInterval);
        }
        
        // 最初のステップを表示
        updateProgressUI(0, progressState.steps[0].name);
        stepIndicators[0].classList.add('active');
        
        // 最初のステップの進行状態を徐々に更新
        startSubProgressAnimation(0);
        
        // 次のステップに進む処理
        progressState.interval = setTimeout(moveToNextStep, progressState.steps[0].duration);
    }
    
    // 段階的なプログレス表示のアニメーション
    function startSubProgressAnimation(stepIndex) {
        const currentStep = progressState.steps[stepIndex];
        const prevStep = stepIndex > 0 ? progressState.steps[stepIndex - 1] : { percent: 0 };
        const startPercent = prevStep.percent;
        const endPercent = currentStep.percent;
        const duration = currentStep.duration;
        const stepSize = (endPercent - startPercent) / (duration / 100); // 100msごとの増加量
        
        let currentPercent = startPercent;
        
        // 既存のサブインターバルをクリア
        if (progressState.subInterval) {
            clearInterval(progressState.subInterval);
        }
        
        // 段階的に進行状況を更新
        progressState.subInterval = setInterval(() => {
            currentPercent = Math.min(currentPercent + stepSize, endPercent);
            updateProgressUI(Math.floor(currentPercent), currentStep.name);
            
            if (currentPercent >= endPercent) {
                clearInterval(progressState.subInterval);
            }
        }, 100);
    }
    
    // 次のステップに進む
    function moveToNextStep() {
        // 現在のステップをインクリメント
        progressState.currentStep = Math.min(
            progressState.currentStep + 1,
            progressState.steps.length - 1
        );
        
        // ステップインジケーターを更新
        updateStepIndicators();
        
        // 現在のステップのアニメーションを開始
        startSubProgressAnimation(progressState.currentStep);
        
        // 最終ステップでなければ、次のステップの準備
        if (progressState.currentStep < progressState.steps.length - 1) {
            progressState.interval = setTimeout(
                moveToNextStep, 
                progressState.steps[progressState.currentStep].duration
            );
        }
    }
    
    // ステップインジケーターを更新
    function updateStepIndicators() {
        // すべてのインジケーターをリセット
        stepIndicators.forEach((indicator, index) => {
            // 現在のステップより前のステップは完了としてマーク
            if (index < progressState.currentStep) {
                indicator.classList.remove('active');
                indicator.classList.add('completed');
            }
            // 現在のステップはアクティブとしてマーク
            else if (index === progressState.currentStep) {
                indicator.classList.add('active');
                indicator.classList.remove('completed');
            }
            // 将来のステップはノーマル状態
            else {
                indicator.classList.remove('active', 'completed');
            }
        });
    }
    
    // プログレスシミュレーションを停止
    function stopProgressSimulation() {
        if (progressState.interval) {
            clearTimeout(progressState.interval);
            progressState.interval = null;
        }
        if (progressState.subInterval) {
            clearInterval(progressState.subInterval);
            progressState.subInterval = null;
        }
    }
    
    // プログレスを100%に設定
    function completeProgress() {
        stopProgressSimulation();
        updateProgressUI(100, '完了');
        
        // すべてのステップを完了としてマーク
        stepIndicators.forEach(indicator => {
            indicator.classList.remove('active');
            indicator.classList.add('completed');
        });
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
        // 既存のトーストを削除
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            document.body.removeChild(existingToast);
        }
        
        // 新しいトースト作成
        const toast = document.createElement('div');
        toast.className = 'toast success-toast';
        toast.innerHTML = `
            <i class="fas fa-check-circle"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(toast);
        
        // アニメーションのために少し待つ
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // 数秒後に消す
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (document.body.contains(toast)) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
    
    // テンプレート表示関数の更新
    function displayTemplates(templates) {
        // テンプレートを状態に保存
        paginationState.allTemplates = templates;
        
        // ページネーション設定
        paginationState.totalPages = Math.ceil(templates.length / paginationState.itemsPerPage);
        paginationState.currentPage = 1;
        
        // ページネーションUIを更新
        updatePaginationUI();
        
        // 最初のページを表示
        displayTemplatesForPage(1);
    }
    
    // 特定のページのテンプレートを表示
    function displayTemplatesForPage(page) {
        // ローディングスピナーを表示
        templatesLoading.classList.add('active');
        
        // 少し遅延させてUIの応答性を向上
        setTimeout(() => {
            // テンプレートコンテナをクリア
            templateContainer.innerHTML = '';
            
            const startIndex = (page - 1) * paginationState.itemsPerPage;
            const endIndex = startIndex + paginationState.itemsPerPage;
            const pageTemplates = paginationState.allTemplates.slice(startIndex, endIndex);
            
            // ページのテンプレートを表示
            pageTemplates.forEach(template => {
                const card = createTemplateCard(template);
                templateContainer.appendChild(card);
            });
            
            // 現在のページを更新
            paginationState.currentPage = page;
            
            // ページネーションUIを更新
            updatePaginationUI();
            
            // ローディングスピナーを非表示
            templatesLoading.classList.remove('active');
            
            // テキストエリアのリサイズを初期化
            initializeTextareas();
        }, 300);
    }
    
    // ページネーションUIを更新
    function updatePaginationUI() {
        // ページ番号を生成
        paginationNumbers.innerHTML = '';
        
        // 総ページ数が1以下の場合はページネーションを非表示
        if (paginationState.totalPages <= 1) {
            document.querySelector('.pagination').style.display = 'none';
            return;
        } else {
            document.querySelector('.pagination').style.display = 'flex';
        }
        
        // 前へボタンの状態を更新
        if (paginationState.currentPage <= 1) {
            prevPageBtn.classList.add('disabled');
        } else {
            prevPageBtn.classList.remove('disabled');
        }
        
        // 次へボタンの状態を更新
        if (paginationState.currentPage >= paginationState.totalPages) {
            nextPageBtn.classList.add('disabled');
        } else {
            nextPageBtn.classList.remove('disabled');
        }
        
        // ページ番号の表示数を制限（ページ数が多い場合）
        const maxVisiblePages = 5;
        let startPage = Math.max(1, paginationState.currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(paginationState.totalPages, startPage + maxVisiblePages - 1);
        
        // 表示範囲の調整
        if (endPage - startPage + 1 < maxVisiblePages && startPage > 1) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }
        
        // 最初のページへのリンク（必要な場合）
        if (startPage > 1) {
            const firstPageBtn = document.createElement('button');
            firstPageBtn.classList.add('page-btn');
            firstPageBtn.textContent = '1';
            
            firstPageBtn.addEventListener('click', () => {
                displayTemplatesForPage(1);
            });
            
            paginationNumbers.appendChild(firstPageBtn);
            
            // 省略記号（必要な場合）
            if (startPage > 2) {
                const ellipsis = document.createElement('span');
                ellipsis.classList.add('pagination-ellipsis');
                ellipsis.textContent = '...';
                paginationNumbers.appendChild(ellipsis);
            }
        }
        
        // ページ番号ボタンを生成
        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.classList.add('page-btn');
            pageBtn.textContent = i;
            
            if (i === paginationState.currentPage) {
                pageBtn.classList.add('current-page');
            }
            
            pageBtn.addEventListener('click', () => {
                if (i !== paginationState.currentPage) {
                    displayTemplatesForPage(i);
                }
            });
            
            paginationNumbers.appendChild(pageBtn);
        }
        
        // 最後のページへのリンク（必要な場合）
        if (endPage < paginationState.totalPages) {
            // 省略記号（必要な場合）
            if (endPage < paginationState.totalPages - 1) {
                const ellipsis = document.createElement('span');
                ellipsis.classList.add('pagination-ellipsis');
                ellipsis.textContent = '...';
                paginationNumbers.appendChild(ellipsis);
            }
            
            const lastPageBtn = document.createElement('button');
            lastPageBtn.classList.add('page-btn');
            lastPageBtn.textContent = paginationState.totalPages;
            
            lastPageBtn.addEventListener('click', () => {
                displayTemplatesForPage(paginationState.totalPages);
            });
            
            paginationNumbers.appendChild(lastPageBtn);
        }
    }
    
    // ページネーションイベントリスナー
    prevPageBtn.addEventListener('click', () => {
        if (paginationState.currentPage > 1) {
            displayTemplatesForPage(paginationState.currentPage - 1);
        }
    });
    
    nextPageBtn.addEventListener('click', () => {
        if (paginationState.currentPage < paginationState.totalPages) {
            displayTemplatesForPage(paginationState.currentPage + 1);
        }
    });
    
    // トースト表示関数
    function showToast(message, duration = 2000) {
        copiedToast.textContent = message;
        copiedToast.classList.add('show');
        
        setTimeout(() => {
            copiedToast.classList.remove('show');
        }, duration);
    }
    
    // コピー操作後のトースト表示を統一
    function showCopiedToast(fieldName = '') {
        const message = fieldName 
            ? `${fieldName}をクリップボードにコピーしました` 
            : 'クリップボードにコピーしました';
        showToast(message);
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
        const templateCardElement = document.querySelector('#template-card').content.cloneNode(true);
        const card = templateCardElement.querySelector('.template-card');
        
        const titleTextarea = card.querySelector('.title');
        const menuTextarea = card.querySelector('.menu');
        const commentTextarea = card.querySelector('.comment');
        const hashtagTextarea = card.querySelector('.hashtag');
        
        const titleCounter = card.querySelector('.title-count');
        const menuCounter = card.querySelector('.menu-count');
        const commentCounter = card.querySelector('.comment-count');
        const hashtagCounter = card.querySelector('.hashtag-count');
        
        // テンプレートのデータをセット
        titleTextarea.value = template.title;
        menuTextarea.value = template.menu;
        commentTextarea.value = template.comment;
        hashtagTextarea.value = template.hashtag;
        
        // タイトルのスタイルを控えめに設定
        titleTextarea.style.color = 'var(--text-color)';
        titleTextarea.style.fontWeight = 'normal';
        
        // 文字数カウンターの更新
        updateCharCount(titleTextarea, titleCounter, 30);
        updateCharCount(menuTextarea, menuCounter, 50);
        updateCharCount(commentTextarea, commentCounter, 100);
        updateCharCount(hashtagTextarea, hashtagCounter, 50);
        
        // テキストエリアのサイズ調整
        autoResizeTextarea(titleTextarea);
        autoResizeTextarea(menuTextarea);
        autoResizeTextarea(commentTextarea);
        autoResizeTextarea(hashtagTextarea);
        
        // アニメーション効果の追加 - カードごとに表示タイミングを少しずらす
        card.style.animationDelay = `${Math.random() * 0.3}s`;
        card.style.animationDuration = '0.5s';
        card.style.animationName = 'scaleIn';
        card.style.animationFillMode = 'backwards';
        
        // テキスト入力イベント設定
        titleTextarea.addEventListener('input', () => {
            updateCharCount(titleTextarea, titleCounter, 30);
            autoResizeTextarea(titleTextarea);
        });
        
        menuTextarea.addEventListener('input', () => {
            updateCharCount(menuTextarea, menuCounter, 50);
            autoResizeTextarea(menuTextarea);
        });
        
        commentTextarea.addEventListener('input', () => {
            updateCharCount(commentTextarea, commentCounter, 100);
            autoResizeTextarea(commentTextarea);
        });
        
        hashtagTextarea.addEventListener('input', () => {
            updateCharCount(hashtagTextarea, hashtagCounter, 50);
            autoResizeTextarea(hashtagTextarea);
        });
        
        // フォーカス時の効果
        const textareas = card.querySelectorAll('textarea');
        textareas.forEach(textarea => {
            textarea.addEventListener('focus', () => {
                textarea.closest('.textarea-container').style.boxShadow = '0 0 0 4px rgba(67, 97, 238, 0.1)';
            });
            
            textarea.addEventListener('blur', () => {
                textarea.closest('.textarea-container').style.boxShadow = '0 2px 5px rgba(0, 0, 0, 0.02)';
            });
        });
        
        // 各フィールドのコピーボタンの機能を追加
        const fieldCopyBtns = card.querySelectorAll('.field-copy-btn');
        fieldCopyBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const fieldType = btn.getAttribute('data-field');
                const textarea = card.querySelector(`.${fieldType}`);
                
                if (!textarea) return;
                
                // テキストをコピー
                navigator.clipboard.writeText(textarea.value).then(() => {
                    // コピー成功表示
                    const originalIcon = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-check"></i>';
                    btn.classList.add('copied');
                    
                    // 元に戻す
                    setTimeout(() => {
                        btn.innerHTML = originalIcon;
                        btn.classList.remove('copied');
                    }, 1500);
                    
                    // 適切なメッセージでトースト表示
                    const fieldLabels = {
                        'title': 'タイトル',
                        'menu': 'メニュー',
                        'comment': 'コメント',
                        'hashtag': 'ハッシュタグ'
                    };
                    showCopiedToast(fieldLabels[fieldType]);
                }).catch(err => {
                    showError('コピーに失敗しました');
                    console.error('コピーに失敗:', err);
                });
            });
        });
        
        // クリップボードコピー機能（全体）
        const copyBtn = card.querySelector('.copy-btn');
        copyBtn.addEventListener('click', () => {
            const text = `【タイトル】
${titleTextarea.value}

【メニュー】
${menuTextarea.value}

【コメント】
${commentTextarea.value}

【ハッシュタグ】
${hashtagTextarea.value}`;
            
            navigator.clipboard.writeText(text).then(() => {
                // コピー成功表示
                copyBtn.innerHTML = '<i class="fas fa-check"></i> コピー完了';
                copyBtn.classList.add('copied');
                
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i> コピー';
                    copyBtn.classList.remove('copied');
                }, 2000);
                
                showCopiedToast('テンプレート全体');
            }).catch(err => {
                showError('コピーに失敗しました');
                console.error('コピーに失敗:', err);
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
    exportAllBtn.addEventListener('click', () => {
        const templates = getTemplatesFromCards();
        if (templates.length === 0) {
            showError('エクスポートするテンプレートがありません');
            return;
        }
        
        // エクスポート選択ダイアログのスタイルを追加
        const exportDialog = document.createElement('div');
        exportDialog.className = 'export-dialog';
        exportDialog.innerHTML = `
            <div class="export-dialog-content">
                <div class="export-dialog-header">
                    <h3>エクスポート形式を選択</h3>
                    <button class="close-btn"><i class="fas fa-times"></i></button>
                </div>
                <div class="export-dialog-body">
                    <button class="export-option" data-format="csv">
                        <i class="fas fa-file-csv"></i>
                        <span>CSV形式</span>
                    </button>
                    <button class="export-option" data-format="txt">
                        <i class="fas fa-file-alt"></i>
                        <span>テキスト形式</span>
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(exportDialog);
        
        // ダイアログスタイル追加
        const style = document.createElement('style');
        style.textContent = `
            .export-dialog {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                animation: fadeIn 0.3s;
            }
            
            .export-dialog-content {
                background-color: white;
                border-radius: var(--border-radius-lg);
                max-width: 400px;
                width: 90%;
                box-shadow: var(--shadow-lg);
                overflow: hidden;
                animation: scaleIn 0.3s;
            }
            
            .export-dialog-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: var(--spacing-md) var(--spacing-lg);
                background: var(--primary-gradient);
                color: white;
            }
            
            .export-dialog-header h3 {
                margin: 0;
                font-size: 1.1rem;
            }
            
            .close-btn {
                background: transparent;
                border: none;
                color: white;
                cursor: pointer;
                font-size: 1.1rem;
                padding: 5px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .export-dialog-body {
                padding: var(--spacing-lg);
                display: flex;
                gap: var(--spacing-md);
            }
            
            .export-option {
                flex: 1;
                background-color: white;
                border: 2px solid var(--border-color);
                border-radius: var(--border-radius-md);
                padding: var(--spacing-lg);
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: var(--spacing-sm);
                cursor: pointer;
                transition: all 0.3s var(--transition-ease);
            }
            
            .export-option:hover {
                border-color: var(--primary-color);
                background-color: rgba(67, 97, 238, 0.05);
                transform: translateY(-5px);
            }
            
            .export-option i {
                font-size: 2rem;
                color: var(--primary-color);
                margin-bottom: var(--spacing-xs);
            }
            
            @media (max-width: 768px) {
                .export-dialog-body {
                    flex-direction: column;
                }
            }
        `;
        document.head.appendChild(style);
        
        // CSV形式でエクスポート
        exportDialog.querySelector('[data-format="csv"]').addEventListener('click', () => {
            const csv = [
                ['タイトル', 'メニュー', 'コメント', 'ハッシュタグ'].join(','),
                ...templates.map(template => [
                    `"${template.title.replace(/"/g, '""')}"`,
                    `"${template.menu.replace(/"/g, '""')}"`,
                    `"${template.comment.replace(/"/g, '""')}"`,
                    `"${template.hashtag.replace(/"/g, '""')}"`,
                ].join(','))
            ].join('\n');
            
            downloadFile(csv, 'hair_templates.csv', 'text/csv');
            showSuccessToast('CSVファイルをダウンロードしました');
            document.body.removeChild(exportDialog);
        });
        
        // テキスト形式でエクスポート
        exportDialog.querySelector('[data-format="txt"]').addEventListener('click', () => {
            const txt = templates.map((template, index) => [
                `■ テンプレート ${index + 1}`,
                `【タイトル】\n${template.title}`,
                `【メニュー】\n${template.menu}`,
                `【コメント】\n${template.comment}`,
                `【ハッシュタグ】\n${template.hashtag}`,
                '='.repeat(40) + '\n'
            ].join('\n'));
            
            downloadFile(txt, 'hair_templates.txt', 'text/plain');
            showSuccessToast('テキストファイルをダウンロードしました');
            document.body.removeChild(exportDialog);
        });
        
        // ダイアログを閉じる
        exportDialog.querySelector('.close-btn').addEventListener('click', () => {
            document.body.removeChild(exportDialog);
        });
        
        // 背景クリックでも閉じる
        exportDialog.addEventListener('click', (e) => {
            if (e.target === exportDialog) {
                document.body.removeChild(exportDialog);
            }
        });
    });
    
    // 全テンプレートをコピー
    copyAllBtn.addEventListener('click', () => {
        const templates = getTemplatesFromCards();
        if (templates.length === 0) {
            showError('コピーするテンプレートがありません');
            return;
        }
        
        const text = templates.map((template, index) => [
            `■ テンプレート ${index + 1}`,
            `【タイトル】\n${template.title}`,
            `【メニュー】\n${template.menu}`,
            `【コメント】\n${template.comment}`,
            `【ハッシュタグ】\n${template.hashtag}`,
            '='.repeat(40)
        ].join('\n\n'));
        
        navigator.clipboard.writeText(text).then(() => {
            showCopiedToast('すべてのテンプレート');
        }).catch(error => {
            showError('コピーに失敗しました');
            console.error('コピーエラー:', error);
        });
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
        // スムーズスクロール
        loadingSpinner.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
                border-radius: var(--border-radius-lg);
                box-shadow: var(--shadow-lg);
                display: flex;
                align-items: center;
                gap: 12px;
                z-index: 1000;
                transform: translateY(100px);
                opacity: 0;
                transition: all 0.4s var(--transition-ease);
                border-left: 4px solid var(--success-color);
            }
            
            .toast.show {
                transform: translateY(0);
                opacity: 1;
            }
            
            .toast.success-toast i {
                color: var(--success-color);
                font-size: 18px;
                background-color: rgba(0, 200, 81, 0.1);
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
            }
            
            .copy-btn.copied {
                background-color: var(--success-color);
                color: white;
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

    // 性別選択の視認性向上対応
    function updateGenderSelectionStyles() {
        const genderOptions = document.querySelectorAll('.gender-option-wrapper');
        
        genderOptions.forEach(option => {
            const radio = option.querySelector('input[type="radio"]');
            if (radio.checked) {
                option.querySelector('.gender-option').classList.add('gender-option-active');
                option.querySelector('.gender-option').classList.remove('gender-option-inactive');
            } else {
                option.querySelector('.gender-option').classList.remove('gender-option-active');
                option.querySelector('.gender-option').classList.add('gender-option-inactive');
            }
        });
    }
    
    // 初期表示時に性別選択のスタイルを適用
    updateGenderSelectionStyles();
    
    // 性別選択変更時のイベントリスナー
    genderRadios.forEach(radio => {
        radio.addEventListener('change', updateGenderSelectionStyles);
    });

    // テキストエリアの初期化関数
    function initializeTextareas() {
        const textareas = document.querySelectorAll('textarea');
        textareas.forEach(textarea => {
            autoResizeTextarea(textarea);
            
            // 文字数カウンターの初期化
            const field = textarea.classList[0];
            const countElement = textarea.closest('.field').querySelector(`.${field}-count`);
            const maxLength = textarea.getAttribute('maxlength');
            
            if (field === 'hashtag') {
                updateHashtagCount(textarea, countElement);
            } else {
                updateCharCount(textarea, countElement, maxLength);
            }
        });
    }
}); 