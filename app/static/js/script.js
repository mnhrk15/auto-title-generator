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
            { name: 'テンプレート生成中...', percent: 85, duration: 10000 },
            { name: '完了', percent: 100, duration: 300 }
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
    
    // 特集キーワード管理クラス
    class FeaturedKeywordsManager {
        constructor() {
            this.keywords = [];
            this.selectedKeyword = null;
            this.lastSelectionTime = null;
            this.container = document.getElementById('featured-keywords-container');
            this.keywordInput = document.getElementById('keyword');
            this.genderRadios = document.querySelectorAll('input[name="gender"]');
        }
        
        async init() {
            try {
                console.log('特集キーワード機能の初期化を開始します');
                
                // ローディング状態を表示
                this.showLoading();
                
                await this.loadFeaturedKeywords();
                this.renderFeaturedKeywords();
                this.setupGenderChangeListeners();
                
                console.log('特集キーワード機能の初期化が完了しました');
                
            } catch (error) {
                console.error('特集キーワードの初期化に失敗:', error);
                
                // エラーの種類に応じた処理
                let errorMessage = '特集キーワードの読み込みに失敗しました';
                let showRetryButton = true;
                
                if (error.message.includes('タイムアウト')) {
                    errorMessage = '特集キーワードの読み込みがタイムアウトしました';
                } else if (error.message.includes('ネットワーク')) {
                    errorMessage = 'ネットワークエラーが発生しました';
                } else if (error.message.includes('サーバーエラー')) {
                    errorMessage = 'サーバーで問題が発生しています';
                    showRetryButton = false; // サーバーエラーの場合はリトライボタンを表示しない
                }
                
                this.showError(errorMessage, showRetryButton);
                
                // 通常機能は継続できることをユーザーに通知
                this.showFallbackNotification();
            }
        }
        
        setupGenderChangeListeners() {
            // 性別ラジオボタンの手動変更を監視
            this.genderRadios.forEach(radio => {
                radio.addEventListener('change', (event) => {
                    // 特集キーワード選択による自動変更でない場合
                    if (this.lastSelectionTime && Date.now() - this.lastSelectionTime < 1000) {
                        return; // 自動選択による変更の場合は何もしない
                    }
                    
                    // 性別変更時に特集キーワードを再読み込み
                    console.log(`性別が変更されました: ${event.target.value}`);
                    this.reloadKeywordsForGender(event.target.value);
                    
                    // 手動変更の場合、特集キーワード選択をクリア
                    if (this.selectedKeyword) {
                        this.clearSelection();
                        
                        // 手動変更のフィードバック
                        const genderLabels = {
                            'ladies': 'レディース',
                            'mens': 'メンズ'
                        };
                        
                        const toast = document.createElement('div');
                        toast.className = 'manual-gender-change-toast';
                        toast.innerHTML = `
                            <i class="fas fa-hand-pointer"></i>
                            <span>性別を手動で「${genderLabels[event.target.value]}」に変更しました</span>
                        `;
                        
                        document.body.appendChild(toast);
                        
                        setTimeout(() => {
                            toast.classList.add('show');
                        }, 10);
                        
                        setTimeout(() => {
                            toast.classList.remove('show');
                            setTimeout(() => {
                                if (document.body.contains(toast)) {
                                    document.body.removeChild(toast);
                                }
                            }, 300);
                        }, 2000);
                    }
                });
            });
        }
        
        async loadFeaturedKeywords(gender = null) {
            try {
                // 現在選択されている性別を取得
                if (!gender) {
                    const selectedGender = document.querySelector('input[name="gender"]:checked');
                    gender = selectedGender ? selectedGender.value : 'ladies';
                }
                
                console.log(`特集キーワードの読み込みを開始します (性別: ${gender})`);
                
                // タイムアウト設定付きでfetch
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒タイムアウト
                
                const response = await fetch(`/api/featured-keywords?gender=${gender}`, {
                    signal: controller.signal,
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error(`特集キーワードAPI HTTPエラー: ${response.status} ${response.statusText}`, errorText);
                    throw new Error(`サーバーエラー (${response.status}): ${response.statusText}`);
                }
                
                const data = await response.json();
                console.log('特集キーワードAPIレスポンス:', data);
                
                // レスポンスデータの検証
                if (!data || typeof data !== 'object') {
                    throw new Error('無効なレスポンス形式です');
                }
                
                // 成功レスポンスの処理
                if (data.success === true || data.success === undefined) {
                    this.keywords = Array.isArray(data.keywords) ? data.keywords : [];
                    
                    // フォールバック情報の処理
                    if (data.fallback) {
                        console.warn('特集キーワード機能はフォールバックモードで動作しています:', data.message);
                        this.showFallbackMessage(data.message);
                    }
                    
                    // 健全性状態の処理
                    if (data.health_status) {
                        console.log('特集キーワード機能の健全性状態:', data.health_status);
                        if (!data.health_status.is_available && data.health_status.last_error) {
                            console.warn('特集キーワード機能に問題があります:', data.health_status.last_error);
                        }
                    }
                    
                    console.log(`特集キーワードを正常に読み込みました: ${this.keywords.length}件`);
                } else {
                    // エラーレスポンスの処理
                    const errorMessage = data.error?.message || data.message || '特集キーワードの取得に失敗しました';
                    throw new Error(errorMessage);
                }
                
            } catch (error) {
                console.error('特集キーワードの取得に失敗:', error);
                
                // エラーの種類に応じた処理
                if (error.name === 'AbortError') {
                    throw new Error('特集キーワードの読み込みがタイムアウトしました');
                } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                    throw new Error('ネットワークエラーが発生しました');
                } else {
                    throw error;
                }
            }
        }
        
        renderFeaturedKeywords() {
            if (!this.container) return;
            
            // ローディング表示を削除
            this.container.innerHTML = '';
            
            if (this.keywords.length === 0) {
                this.container.innerHTML = `
                    <div class="featured-keywords-empty">
                        <i class="fas fa-info-circle"></i>
                        現在、特集キーワードはありません
                    </div>
                `;
                return;
            }
            
            // 特集キーワードボタンを生成
            this.keywords.forEach(keyword => {
                const button = this.createKeywordButton(keyword);
                this.container.appendChild(button);
            });
        }
        
        createKeywordButton(keyword) {
            const button = document.createElement('button');
            button.className = 'featured-keyword-btn';
            button.innerHTML = `
                <i class="fas fa-star"></i>
                <span>${keyword.name}</span>
            `;
            
            // データ属性を追加してキーワード情報を保存
            button.setAttribute('data-keyword', keyword.keyword);
            button.setAttribute('data-name', keyword.name);
            button.setAttribute('data-gender', keyword.gender);
            
            // クリックイベントハンドラーを追加
            button.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                
                // ボタンの無効化（連続クリック防止）
                button.disabled = true;
                
                try {
                    this.selectFeaturedKeyword(keyword);
                } catch (error) {
                    console.error('特集キーワード選択エラー:', error);
                    // エラー時のフィードバック
                    this.showErrorFeedback('キーワードの選択に失敗しました');
                } finally {
                    // ボタンを再度有効化
                    setTimeout(() => {
                        button.disabled = false;
                    }, 500);
                }
            });
            
            // キーボードアクセシビリティ対応
            button.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    button.click();
                }
            });
            
            // ホバー効果の強化
            button.addEventListener('mouseenter', () => {
                if (!button.classList.contains('active')) {
                    button.style.transform = 'translateY(-2px) scale(1.02)';
                }
            });
            
            button.addEventListener('mouseleave', () => {
                if (!button.classList.contains('active')) {
                    button.style.transform = '';
                }
            });
            
            // クリック効果
            button.addEventListener('mousedown', () => {
                button.style.transform = 'translateY(0) scale(0.98)';
            });
            
            button.addEventListener('mouseup', () => {
                if (button.classList.contains('active')) {
                    button.style.transform = 'translateY(-2px)';
                } else {
                    button.style.transform = '';
                }
            });
            
            // フォーカス効果
            button.addEventListener('focus', () => {
                button.style.outline = '2px solid rgba(255, 255, 255, 0.5)';
                button.style.outlineOffset = '2px';
            });
            
            button.addEventListener('blur', () => {
                button.style.outline = '';
                button.style.outlineOffset = '';
            });
            
            // アクセシビリティ属性を設定
            button.setAttribute('role', 'button');
            button.setAttribute('aria-pressed', 'false');
            button.setAttribute('tabindex', '0');
            
            return button;
        }
        
        selectFeaturedKeyword(keyword) {
            // 同じキーワードが既に選択されている場合は選択解除
            if (this.selectedKeyword && this.selectedKeyword.keyword === keyword.keyword) {
                this.deselectFeaturedKeyword();
                return;
            }
            
            // 既存の選択状態をクリア
            this.clearSelection();
            
            // キーワードを入力欄に設定
            if (this.keywordInput) {
                // キーワードを設定
                this.keywordInput.value = keyword.keyword;
                
                // 入力欄にフォーカスを当てる
                this.keywordInput.focus();
                
                // 入力イベントを発火させて他の処理をトリガー
                this.keywordInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
            
            // 性別を自動選択
            this.selectGender(keyword.gender);
            
            // 選択状態を視覚的に表示
            this.updateButtonState(keyword);
            
            // 選択されたキーワードを記録
            this.selectedKeyword = keyword;
            
            // 選択時刻を記録（手動選択判定用）
            this.lastSelectionTime = Date.now();
            
        }
        
        deselectFeaturedKeyword() {
            // 選択解除のフィードバック
            if (this.selectedKeyword) {
                const toast = document.createElement('div');
                toast.className = 'featured-deselection-toast';
                toast.innerHTML = `
                    <i class="fas fa-times-circle"></i>
                    <span>特集キーワード「${this.selectedKeyword.name}」の選択を解除しました</span>
                `;
                
                document.body.appendChild(toast);
                
                setTimeout(() => {
                    toast.classList.add('show');
                }, 10);
                
                setTimeout(() => {
                    toast.classList.remove('show');
                    setTimeout(() => {
                        if (document.body.contains(toast)) {
                            document.body.removeChild(toast);
                        }
                    }, 300);
                }, 2000);
            }
            
            // 入力欄をクリア
            if (this.keywordInput) {
                this.keywordInput.value = '';
                this.keywordInput.focus();
                this.keywordInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
            
            // 選択状態をクリア
            this.clearSelection();
        }
        
        selectGender(gender) {
            // 現在選択されている性別を取得
            const currentGender = document.querySelector('input[name="gender"]:checked')?.value;
            
            // 既に同じ性別が選択されている場合は何もしない
            if (currentGender === gender) {
                return;
            }
            
            // 異なる性別が選択されている場合の処理
            if (currentGender && currentGender !== gender) {
                // ユーザーが手動で選択した可能性があるかチェック
                const wasManuallySelected = this.checkIfManuallySelected();
                
                if (wasManuallySelected) {
                    // 確認ダイアログを表示
                    const genderLabels = {
                        'ladies': 'レディース',
                        'mens': 'メンズ'
                    };
                    
                    const currentLabel = genderLabels[currentGender];
                    const newLabel = genderLabels[gender];
                    
                    if (!confirm(`現在の性別設定「${currentLabel}」を「${newLabel}」に変更しますか？`)) {
                        return; // ユーザーがキャンセルした場合は変更しない
                    }
                }
            }
            
            // 性別を設定
            this.genderRadios.forEach(radio => {
                if (radio.value === gender) {
                    radio.checked = true;
                    // changeイベントを発火させて他の処理をトリガー
                    radio.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    radio.checked = false;
                }
            });
            
            // 性別変更のフィードバック
            this.showGenderChangeFeedback(gender);
        }
        
        checkIfManuallySelected() {
            // 最後の特集キーワード選択から一定時間が経過している場合、
            // ユーザーが手動で変更した可能性が高い
            if (!this.lastSelectionTime) {
                return true; // 特集キーワードが選択されていない場合は手動選択とみなす
            }
            
            const timeSinceLastSelection = Date.now() - this.lastSelectionTime;
            return timeSinceLastSelection > 3000; // 3秒以上経過していれば手動選択とみなす
        }
        
        showGenderChangeFeedback(gender) {
            const genderLabels = {
                'ladies': 'レディース',
                'mens': 'メンズ'
            };
            
            // 性別変更のフィードバックを表示
            const toast = document.createElement('div');
            toast.className = 'gender-change-toast';
            toast.innerHTML = `
                <i class="fas fa-${gender === 'ladies' ? 'female' : 'male'}"></i>
                <span>性別を「${genderLabels[gender]}」に設定しました</span>
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
            }, 1500);
        }
        
        updateButtonState(selectedKeyword) {
            const buttons = this.container.querySelectorAll('.featured-keyword-btn');
            buttons.forEach(button => {
                const buttonText = button.querySelector('span').textContent;
                if (buttonText === selectedKeyword.name) {
                    // アクティブ状態に設定
                    button.classList.add('active');
                    button.setAttribute('aria-pressed', 'true');
                    
                    // アクティブ状態のアニメーション効果
                    button.style.animation = 'none';
                    setTimeout(() => {
                        button.style.animation = '';
                    }, 10);
                } else {
                    // 非アクティブ状態に設定
                    button.classList.remove('active');
                    button.setAttribute('aria-pressed', 'false');
                }
            });
        }
        
        async reloadKeywordsForGender(gender) {
            try {
                console.log(`性別 ${gender} の特集キーワードを再読み込みします`);
                
                // ローディング状態を表示
                this.showLoading();
                
                // 現在の選択をクリア
                this.clearSelection();
                
                // 新しい性別のキーワードを読み込み
                await this.loadFeaturedKeywords(gender);
                this.renderFeaturedKeywords();
                
                console.log(`性別 ${gender} の特集キーワード再読み込みが完了しました`);
                
            } catch (error) {
                console.error('特集キーワードの再読み込みに失敗:', error);
                this.showError('特集キーワードの更新に失敗しました', true);
            }
        }
        
        clearSelection() {
            const buttons = this.container.querySelectorAll('.featured-keyword-btn');
            buttons.forEach(button => {
                // アクティブ状態をクリア
                button.classList.remove('active');
                button.setAttribute('aria-pressed', 'false');
                
                // クリア時のアニメーション効果
                if (button.classList.contains('active')) {
                    button.style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        button.style.transform = '';
                    }, 150);
                }
            });
            
            // 選択状態をリセット
            this.selectedKeyword = null;
            this.lastSelectionTime = null;
        }
        
        showLoading() {
            if (!this.container) return;
            
            this.container.innerHTML = `
                <div class="featured-keywords-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>特集キーワードを読み込み中...</span>
                </div>
            `;
        }
        
        showError(message = '特集キーワードの読み込みに失敗しました', showRetryButton = true) {
            if (!this.container) return;
            
            const retryButtonHtml = showRetryButton ? `
                <button class="featured-keywords-retry-btn" onclick="featuredKeywordsManager.retry()">
                    <i class="fas fa-redo"></i>
                    再試行
                </button>
            ` : '';
            
            this.container.innerHTML = `
                <div class="featured-keywords-error">
                    <div class="error-content">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span class="error-message">${message}</span>
                    </div>
                    ${retryButtonHtml}
                </div>
            `;
        }
        
        showFallbackMessage(message) {
            if (!this.container) return;
            
            // 既存のコンテンツの上に警告メッセージを表示
            const warningDiv = document.createElement('div');
            warningDiv.className = 'featured-keywords-warning';
            warningDiv.innerHTML = `
                <i class="fas fa-info-circle"></i>
                <span>${message}</span>
            `;
            
            this.container.insertBefore(warningDiv, this.container.firstChild);
            
            // 数秒後に自動で消す
            setTimeout(() => {
                if (warningDiv.parentNode) {
                    warningDiv.parentNode.removeChild(warningDiv);
                }
            }, 5000);
        }
        
        showFallbackNotification() {
            // 通常機能は継続できることをユーザーに通知
            const notification = document.createElement('div');
            notification.className = 'featured-fallback-notification';
            notification.innerHTML = `
                <div class="notification-content">
                    <i class="fas fa-info-circle"></i>
                    <div class="notification-text">
                        <strong>特集キーワード機能が利用できません</strong>
                        <p>通常のテンプレート生成機能は引き続きご利用いただけます。</p>
                    </div>
                    <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // アニメーションで表示
            setTimeout(() => {
                notification.classList.add('show');
            }, 100);
            
            // 10秒後に自動で消す
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.classList.remove('show');
                    setTimeout(() => {
                        if (notification.parentNode) {
                            notification.parentNode.removeChild(notification);
                        }
                    }, 300);
                }
            }, 10000);
        }
        
        async retry() {
            console.log('特集キーワードの再試行を開始します');
            
            try {
                // ローディング状態を表示
                this.showLoading();
                
                // 少し待ってから再試行（ユーザビリティ向上）
                await new Promise(resolve => setTimeout(resolve, 500));
                
                await this.loadFeaturedKeywords();
                this.renderFeaturedKeywords();
                
                console.log('特集キーワードの再試行が成功しました');
                
                // 成功通知
                this.showRetrySuccessToast();
                
            } catch (error) {
                console.error('特集キーワードの再試行に失敗:', error);
                
                let errorMessage = '再試行に失敗しました';
                let showRetryButton = true;
                
                if (error.message.includes('タイムアウト')) {
                    errorMessage = '再試行がタイムアウトしました';
                } else if (error.message.includes('ネットワーク')) {
                    errorMessage = 'ネットワークエラーが継続しています';
                } else if (error.message.includes('サーバーエラー')) {
                    errorMessage = 'サーバーの問題が継続しています';
                    showRetryButton = false;
                }
                
                this.showError(errorMessage, showRetryButton);
            }
        }
        
        showRetrySuccessToast() {
            const toast = document.createElement('div');
            toast.className = 'featured-retry-success-toast';
            toast.innerHTML = `
                <i class="fas fa-check-circle"></i>
                <span>特集キーワードを正常に読み込みました</span>
            `;
            
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.classList.add('show');
            }, 10);
            
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    if (document.body.contains(toast)) {
                        document.body.removeChild(toast);
                    }
                }, 300);
            }, 3000);
        }
        
        
        showErrorFeedback(message) {
            // エラーフィードバックを表示
            const toast = document.createElement('div');
            toast.className = 'featured-error-toast';
            toast.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i>
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
            }, 2500);
        }
    }
    
    // 特集キーワードマネージャーを初期化
    const featuredKeywordsManager = new FeaturedKeywordsManager();
    featuredKeywordsManager.init();
    
    // 特集キーワードエラー時のフォールバック通知
    function showFeaturedErrorFallbackNotification() {
        const notification = document.createElement('div');
        notification.className = 'featured-error-fallback-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-info-circle"></i>
                <div class="notification-text">
                    <strong>特集キーワード機能でエラーが発生しました</strong>
                    <p>特集キーワードの選択を解除して、通常のテンプレート生成をお試しください。</p>
                </div>
                <div class="notification-actions">
                    <button class="notification-action-btn" onclick="featuredKeywordsManager.clearSelection(); this.parentElement.parentElement.parentElement.remove();">
                        <i class="fas fa-times-circle"></i>
                        選択を解除
                    </button>
                    <button class="notification-close" onclick="this.parentElement.parentElement.parentElement.remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // アニメーションで表示
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // 15秒後に自動で消す
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.remove('show');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, 15000);
    }
    
    // 初期アニメーション
    animateElements();
    
    // フォーカス処理
    keywordInput.focus();

    // キーワード入力欄の変更時に特集キーワード選択をクリア
    keywordInput.addEventListener('input', () => {
        if (featuredKeywordsManager.selectedKeyword) {
            const currentValue = keywordInput.value.trim();
            const selectedValue = featuredKeywordsManager.selectedKeyword.keyword;
            
            // 入力値が選択された特集キーワードと異なる場合、選択をクリア
            if (currentValue !== selectedValue) {
                featuredKeywordsManager.clearSelection();
            }
        }
    });

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
        const season = document.getElementById('season').value;
        const model = 'gemini-2.5-flash'; // デフォルトでGemini Flashを使用
        
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
            // タイムアウト設定付きでfetch
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000); // 60秒タイムアウト
            
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ keyword, gender, season, model }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`テンプレート生成API HTTPエラー: ${response.status} ${response.statusText}`, errorText);
                throw new Error(`サーバーエラー (${response.status}): ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('テンプレート生成APIレスポンス:', data);
            
            // プログレスを100%に設定
            completeProgress();
            
            if (data.success) {
                // 特集キーワード対応テンプレートの場合の特別な処理
                if (data.is_featured && data.featured_keyword_info) {
                    const featuredName = data.featured_keyword_info.name;
                    console.log(`特集キーワード対応テンプレートが生成されました: ${featuredName}`);
                    
                    // 特集対応テンプレート生成の成功通知
                    showFeaturedSuccessToast(featuredName, data.templates.length);
                    
                    // 特集テンプレートであることを視覚的に示すための追加情報
                    if (data.templates && data.templates.length > 0) {
                        data.templates.forEach(template => {
                            template._is_featured = true; // フロントエンド用フラグ
                            template._featured_keyword_name = featuredName;
                        });
                    }
                } else if (data.is_featured) {
                    // 特集キーワードだが詳細情報がない場合
                    console.log('特集キーワード対応テンプレートが生成されました（詳細情報なし）');
                    showSuccessToast('特集対応テンプレートを生成しました ⭐');
                } else {
                    // 通常テンプレートの場合
                    showSuccessToast('テンプレートを生成しました');
                }
                
                displayTemplates(data.templates);
                showResults();
                
                // 結果表示領域までスクロール
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                // エラーレスポンスの処理
                const errorMessage = data.error?.message || data.message || '不明なエラーが発生しました。';
                const errorCode = data.error?.code || 'UNKNOWN_ERROR';
                
                console.error('テンプレート生成エラー:', errorCode, errorMessage);
                
                // エラーコードに応じた処理
                if (errorCode === 'FEATURED_KEYWORDS_ERROR') {
                    showError('特集キーワード機能でエラーが発生しましたが、通常のテンプレート生成を試行できます。');
                    
                    // 特集キーワード選択をクリアして通常生成を促す
                    if (featuredKeywordsManager.selectedKeyword) {
                        featuredKeywordsManager.clearSelection();
                        showFeaturedErrorFallbackNotification();
                    }
                } else if (errorCode === 'NO_RESULTS_FOUND') {
                    showError('一致するヘアスタイルが見つかりませんでした。別のキーワードをお試しください。');
                } else if (errorCode === 'VALIDATION_ERROR') {
                    showError(errorMessage);
                } else {
                    showError(errorMessage);
                }
            }
        } catch (error) {
            console.error('テンプレート生成中にエラー:', error);
            
            // プログレスを完了に設定
            completeProgress();
            
            // エラーの種類に応じた処理
            let errorMessage = 'テンプレートの生成中にエラーが発生しました。';
            
            if (error.name === 'AbortError') {
                errorMessage = 'テンプレート生成がタイムアウトしました。もう一度お試しください。';
            } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorMessage = 'ネットワークエラーが発生しました。インターネット接続を確認してください。';
            } else if (error.message.includes('サーバーエラー')) {
                errorMessage = 'サーバーで問題が発生しています。しばらく時間をおいて再度お試しください。';
            }
            
            showError(errorMessage);
            
            // 特集キーワードが選択されている場合の追加処理
            if (featuredKeywordsManager.selectedKeyword) {
                setTimeout(() => {
                    showFeaturedErrorFallbackNotification();
                }, 2000);
            }
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
    
    // 特集対応テンプレート生成成功トースト表示
    function showFeaturedSuccessToast(featuredName, templateCount) {
        // 既存のトーストを削除
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            document.body.removeChild(existingToast);
        }
        
        // 新しい特集対応トースト作成
        const toast = document.createElement('div');
        toast.className = 'toast featured-success-toast';
        toast.innerHTML = `
            <i class="fas fa-star"></i>
            <div class="toast-content">
                <div class="toast-title">特集対応テンプレート生成完了！</div>
                <div class="toast-message">「${featuredName}」の特集テンプレート ${templateCount}件を生成しました</div>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // アニメーションのために少し待つ
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // 少し長めに表示（特集対応の重要性を強調）
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (document.body.contains(toast)) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, 4000);
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
        
        // 特集対応テンプレート識別機能の実装
        const featuredIndicator = card.querySelector('.featured-indicator');
        
        // 特集対応テンプレートの場合の視覚的識別マーク
        if (template.is_featured || template._is_featured) {
            // 特集対応マークを表示
            featuredIndicator.style.display = 'flex';
            
            // カード全体に特集スタイルを適用
            card.classList.add('featured');
            
            // 特集キーワード名がある場合はツールチップに表示
            const featuredKeywordName = template.featured_keyword_name || template._featured_keyword_name;
            if (featuredKeywordName) {
                featuredIndicator.title = `特集キーワード: ${featuredKeywordName}`;
                
                // 特集キーワード名をインジケーターのテキストに表示
                const indicatorText = featuredIndicator.querySelector('span');
                if (indicatorText) {
                    indicatorText.textContent = `特集対応 (${featuredKeywordName})`;
                }
            }
            
            // 特集対応テンプレートであることをログに記録
            console.log(`特集対応テンプレートを表示: ${template.title} (キーワード: ${featuredKeywordName || '不明'})`);
        } else {
            // 通常テンプレートの場合は特集マークを非表示
            featuredIndicator.style.display = 'none';
            card.classList.remove('featured');
        }
        
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
        const templates = paginationState.allTemplates;
        if (!templates || templates.length === 0) {
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
            const csvHeader = ['タイトル', 'メニュー', 'コメント', 'ハッシュタグ'].join(',');
            const csvRows = templates.map(template => [
                `"${template.title.replace(/"/g, '""')}"`,
                `"${template.menu.replace(/"/g, '""')}"`,
                `"${template.comment.replace(/"/g, '""')}"`,
                `"${(Array.isArray(template.hashtag) ? template.hashtag.join(' ') : '').replace(/"/g, '""')}"`,
            ].join(','));
            
            // BOMを追加し、ヘッダーと行を結合
            const csvContent = '\uFEFF' + csvHeader + '\n' + csvRows.join('\n');
            
            downloadFile(csvContent, 'hair_templates.csv', 'text/csv;charset=utf-8'); // charsetを指定
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
        const templates = paginationState.allTemplates;
        if (!templates || templates.length === 0) {
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
            
            /* 特集対応テンプレート成功トースト */
            .toast.featured-success-toast {
                background: linear-gradient(135deg, #ffd700, #ffed4e);
                color: #2b2d42;
                border-left: 4px solid #ffb700;
                min-width: 350px;
                padding: 16px 24px;
                box-shadow: 0 8px 25px rgba(255, 215, 0, 0.3);
            }
            
            .toast.featured-success-toast i {
                color: #2b2d42;
                font-size: 20px;
                background-color: rgba(43, 45, 66, 0.1);
                width: 35px;
                height: 35px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                animation: featuredToastStar 2s ease-in-out infinite alternate;
            }
            
            .toast-content {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            
            .toast-title {
                font-weight: 700;
                font-size: 14px;
                color: #2b2d42;
            }
            
            .toast-message {
                font-size: 13px;
                color: #2b2d42;
                opacity: 0.9;
            }
            
            @keyframes featuredToastStar {
                0% {
                    transform: scale(1);
                    box-shadow: 0 0 5px rgba(255, 215, 0, 0.3);
                }
                100% {
                    transform: scale(1.1);
                    box-shadow: 0 0 15px rgba(255, 215, 0, 0.6);
                }
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