window.ResultsState = {
    visualizationMode: 'video',

    scene: null,
    camera: null,
    renderer: null,
    controls: null,
    skeleton: null,
    animationFrameId: null,
    framesData: [],

    currentSkeletonFrameIndex: 0,
    isSkeletonAnimating: false,
    skeletonSpeed: 1.0,
    lastSkeletonAnimationTime: 0,

    videoElement: null,
    videoCanvas: null,
    videoContext: null,
    isVideoPlaying: false,
    isVideoLoopRendering: false,
    videoInitialized: false,
    showOverlay: true,

    speedOptions: [
        { value: 0, speed: 0.25, label: '0.25x' },
        { value: 1, speed: 0.5, label: '0.5x' },
        { value: 2, speed: 0.75, label: '0.75x' },
        { value: 3, speed: 1.0, label: '1.0x' },
        { value: 4, speed: 1.25, label: '1.25x' },
        { value: 5, speed: 1.5, label: '1.5x' },
        { value: 6, speed: 2.0, label: '2.0x' }
    ]
};

window.ResultsUtils = {
    getMetricObject: function (key) {
        return analysisData?.overallMetrics?.[key] || null;
    },

    getMetricValue: function (key) {
        const metric = analysisData?.overallMetrics?.[key] || null;
        if (!metric || metric.value === null || metric.value === undefined) return null;
        const num = Number(metric.value);
        return Number.isFinite(num) ? num : null;
    },

    getMetricUnit: function (key, fallback = '') {
        const metric = analysisData?.overallMetrics?.[key] || null;
        return metric?.unit || fallback;
    },

    getMetricConfidence: function (key) {
        const metric = analysisData?.overallMetrics?.[key] || null;
        if (!metric || metric.confidence === null || metric.confidence === undefined) return null;
        const num = Number(metric.confidence);
        return Number.isFinite(num) ? num : null;
    },

    formatConfidence: function (value) {
        if (value === null || value === undefined || Number.isNaN(value)) return '置信度 --';
        return `置信度 ${Math.round(value * 100)}%`;
    },

    escapeHtml: function (text) {
        return String(text ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }
};

function setVisualizationMode(mode) {
    const state = window.ResultsState;
    state.visualizationMode = mode;

    const skeletonBtn = document.getElementById('modeSkeletonBtn');
    const videoBtn = document.getElementById('modeVideoBtn');
    const titleEl = document.getElementById('visualizationTitle');
    const videoPanel = document.getElementById('videoPanel');
    const skeletonPanel = document.getElementById('skeletonPanel');
    const overlayOptions = document.getElementById('overlayOptions');

    if (skeletonBtn) skeletonBtn.classList.toggle('active', mode === 'skeleton');
    if (videoBtn) videoBtn.classList.toggle('active', mode === 'video');

    const titleMap = {
        skeleton: '动作复核视图',
        video: '动作复核视图'
    };

    if (titleEl) titleEl.innerHTML = `<i class="bi bi-diagram-3"></i> ${titleMap[mode]}`;

    if (mode === 'skeleton') {
        if (videoPanel) videoPanel.style.display = 'none';
        if (skeletonPanel) skeletonPanel.style.display = 'block';
        if (overlayOptions) overlayOptions.style.display = 'none';
    } else {
        if (videoPanel) videoPanel.style.display = 'block';
        if (skeletonPanel) skeletonPanel.style.display = 'block';
        if (overlayOptions) overlayOptions.style.display = 'block';
        if (window.ResultsVideo?.initVideo) {
            try {
                window.ResultsVideo.initVideo();
            } catch (err) {
                console.error('initVideo 失败:', err);
            }
        }
    }
}

window.setVisualizationMode = setVisualizationMode;

document.addEventListener('DOMContentLoaded', function () {
    console.log('analysisData =', analysisData);
    console.log('issues =', analysisData?.issues);
    console.log('overallMetrics =', analysisData?.overallMetrics);

    if (window.ResultsMetrics) {
        try {
            window.ResultsMetrics.renderSummary();
        } catch (err) {
            console.error('renderSummary 失败:', err);
        }

        try {
            window.ResultsMetrics.renderMetricCards();
        } catch (err) {
            console.error('renderMetricCards 失败:', err);
        }

        try {
            window.ResultsMetrics.renderIssues();
        } catch (err) {
            console.error('renderIssues 失败:', err);
        }

        try {
            window.ResultsMetrics.renderQuickNotes();
        } catch (err) {
            console.error('renderQuickNotes 失败:', err);
        }
    }

    if (window.ResultsCharts) {
        try {
            window.ResultsCharts.renderMetricCharts();
        } catch (err) {
            console.error('renderMetricCharts 失败:', err);
        }
    }

    if (window.ResultsSkeleton) {
        try {
            window.ResultsSkeleton.init3DScene();
        } catch (err) {
            console.error('init3DScene 失败:', err);
        }
    }

    try {
        setVisualizationMode('video');
    } catch (err) {
        console.error('setVisualizationMode 失败:', err);
    }
});

window.addEventListener('beforeunload', function () {
    const state = window.ResultsState;
    if (state.animationFrameId) cancelAnimationFrame(state.animationFrameId);
    if (state.renderer) state.renderer.dispose();
    if (state.videoElement) state.videoElement.pause();
});