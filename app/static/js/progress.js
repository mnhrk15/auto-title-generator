// 生成中のプログレスバー（疑似進捗）。
//
// 実測平均 25 秒の生成処理に合わせ、3 ステップ (合計 24 秒) + creep フェーズで構成。
// 100% は API 応答時にのみ completeProgress() で設定する。

import { el } from './dom.js';

const STEPS = [
    { name: 'スクレイピング中...', percent: 25, duration: 7000 },
    { name: 'トレンド分析中...', percent: 35, duration: 3000 },
    { name: 'テンプレート生成中...', percent: 90, duration: 14000 },
];

const SUB_ANIMATION_TICK_MS = 100;
const CREEP_TICK_MS = 1200;
const CREEP_CEILING = 99;

const state = {
    currentStep: 0,
    currentPercent: 0,
    stepTimer: null,
    subInterval: null,
    creepInterval: null,
};

function updateProgressUI(percent, stepName) {
    el.progressFill.style.width = `${percent}%`;
    el.progressPercent.textContent = `${percent}%`;
    el.progressStep.textContent = stepName;
    el.loadingMessage.textContent = stepName;
    el.progressBar?.setAttribute('aria-valuenow', String(percent));
}

/** ステップインジケーターを現在のステップに合わせて塗り分ける */
function updateStepIndicators() {
    el.stepIndicators.forEach((indicator, index) => {
        if (index < state.currentStep) {
            indicator.classList.remove('active');
            indicator.classList.add('completed');
        } else if (index === state.currentStep) {
            indicator.classList.add('active');
            indicator.classList.remove('completed');
        } else {
            indicator.classList.remove('active', 'completed');
        }
    });
}

/** ステップ内で進捗を滑らかに進める */
function startSubProgressAnimation(stepIndex) {
    const currentStep = STEPS[stepIndex];
    const startPercent = stepIndex > 0 ? STEPS[stepIndex - 1].percent : 0;
    const endPercent = currentStep.percent;
    const stepSize = (endPercent - startPercent) / (currentStep.duration / SUB_ANIMATION_TICK_MS);

    state.currentPercent = startPercent;

    clearInterval(state.subInterval);
    state.subInterval = setInterval(() => {
        state.currentPercent = Math.min(state.currentPercent + stepSize, endPercent);
        updateProgressUI(Math.floor(state.currentPercent), currentStep.name);

        if (state.currentPercent >= endPercent) {
            clearInterval(state.subInterval);
            state.subInterval = null;
        }
    }, SUB_ANIMATION_TICK_MS);
}

/** 上限に達した後、API 応答待ちの間 99% へ漸近させる */
function startCreepPhase() {
    clearInterval(state.subInterval);
    state.subInterval = null;
    clearInterval(state.creepInterval);

    state.creepInterval = setInterval(() => {
        const remaining = CREEP_CEILING - state.currentPercent;
        if (remaining <= 0.1) return;
        state.currentPercent += remaining * 0.10;
        updateProgressUI(Math.floor(state.currentPercent), 'テンプレート生成中...');
    }, CREEP_TICK_MS);
}

function moveToNextStep() {
    state.currentStep = Math.min(state.currentStep + 1, STEPS.length - 1);
    updateStepIndicators();
    startSubProgressAnimation(state.currentStep);

    const duration = STEPS[state.currentStep].duration;
    const isLastStep = state.currentStep >= STEPS.length - 1;
    // 最終ステップ完了後は creep フェーズへ移行（API 応答待ちを表現）
    state.stepTimer = setTimeout(isLastStep ? startCreepPhase : moveToNextStep, duration);
}

export function stopProgressSimulation() {
    clearTimeout(state.stepTimer);
    clearInterval(state.subInterval);
    clearInterval(state.creepInterval);
    state.stepTimer = null;
    state.subInterval = null;
    state.creepInterval = null;
}

export function resetProgress() {
    // 残存タイマーがあれば全停止（連打や前回エラー時の状態汚染を防ぐ）
    stopProgressSimulation();
    state.currentStep = 0;
    state.currentPercent = 0;
    updateProgressUI(0, STEPS[0].name);

    el.stepIndicators.forEach((indicator) => indicator.classList.remove('active', 'completed'));
    el.stepIndicators[0]?.classList.add('active');
}

export function startProgressSimulation() {
    stopProgressSimulation();

    updateProgressUI(0, STEPS[0].name);
    el.stepIndicators[0]?.classList.add('active');
    startSubProgressAnimation(0);
    state.stepTimer = setTimeout(moveToNextStep, STEPS[0].duration);
}

export function completeProgress() {
    stopProgressSimulation();
    updateProgressUI(100, '完了');
    el.stepIndicators.forEach((indicator) => {
        indicator.classList.remove('active');
        indicator.classList.add('completed');
    });
}
