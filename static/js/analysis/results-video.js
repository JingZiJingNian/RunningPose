(function () {
    const state = window.ResultsState;

    function getCurrentVideoFrameIndex() {
        if (!state.videoElement || !state.framesData.length) return 0;

        const fps = Number(analysisData.videoInfo.fps || 30);
        const startTime = Number(analysisData.videoInfo.startTime || 0);
        const localTime = Math.max(0, state.videoElement.currentTime - startTime);
        const frameIndex = Math.floor(localTime * fps);

        return Math.max(0, Math.min(frameIndex, state.framesData.length - 1));
    }

    function resizeVideoCanvas() {
        if (!state.videoCanvas) return;

        const rect = state.videoCanvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        state.videoCanvas.width = Math.max(1, Math.floor(rect.width * dpr));
        state.videoCanvas.height = Math.max(1, Math.floor(rect.height * dpr));

        if (state.videoContext) {
            state.videoContext.setTransform(1, 0, 0, 1, 0, 0);
            state.videoContext.scale(dpr, dpr);
        }

        drawVideoFrame();
    }

    function drawVideoFrame() {
        if (!state.videoContext || !state.videoCanvas || !state.videoElement) return;

        const rect = state.videoCanvas.getBoundingClientRect();
        const canvasWidth = rect.width;
        const canvasHeight = rect.height;

        state.videoContext.clearRect(0, 0, canvasWidth, canvasHeight);
        state.videoContext.fillStyle = '#000';
        state.videoContext.fillRect(0, 0, canvasWidth, canvasHeight);

        const videoWidth = state.videoElement.videoWidth;
        const videoHeight = state.videoElement.videoHeight;
        if (!videoWidth || !videoHeight) return;

        const scale = Math.min(canvasWidth / videoWidth, canvasHeight / videoHeight);
        const drawWidth = videoWidth * scale;
        const drawHeight = videoHeight * scale;
        const offsetX = (canvasWidth - drawWidth) / 2;
        const offsetY = (canvasHeight - drawHeight) / 2;

        if (state.videoElement.readyState >= 2) {
            try {
                state.videoContext.drawImage(state.videoElement, offsetX, offsetY, drawWidth, drawHeight);
            } catch (e) {
                console.error('绘制视频帧失败:', e);
                return;
            }
        } else {
            return;
        }

        if (!state.showOverlay || !state.framesData.length) return;

        const currentVideoFrameIndex = getCurrentVideoFrameIndex();
        const frameData = state.framesData[currentVideoFrameIndex];
        if (!frameData || !frameData.landmarks_2d || !frameData.landmarks_2d.length) return;

        const landmarks = frameData.landmarks_2d;
        const connections = [
            [11,12],[11,13],[13,15],[12,14],[14,16],
            [11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28],
            [27,29],[29,31],[28,30],[30,32]
        ];

        state.videoContext.lineWidth = 2;
        state.videoContext.strokeStyle = 'rgba(79, 70, 229, 0.95)';
        state.videoContext.fillStyle = 'rgba(14, 165, 233, 0.95)';

        connections.forEach(([a, b]) => {
            if (landmarks[a] && landmarks[b]) {
                const x1 = offsetX + landmarks[a].x * drawWidth;
                const y1 = offsetY + landmarks[a].y * drawHeight;
                const x2 = offsetX + landmarks[b].x * drawWidth;
                const y2 = offsetY + landmarks[b].y * drawHeight;

                state.videoContext.beginPath();
                state.videoContext.moveTo(x1, y1);
                state.videoContext.lineTo(x2, y2);
                state.videoContext.stroke();
            }
        });

        landmarks.forEach((lm) => {
            if (lm && (lm.visibility === undefined || lm.visibility > 0.1)) {
                const x = offsetX + lm.x * drawWidth;
                const y = offsetY + lm.y * drawHeight;

                state.videoContext.beginPath();
                state.videoContext.arc(x, y, 3, 0, Math.PI * 2);
                state.videoContext.fill();
            }
        });
    }

    function updateVideoPlayButton() {
        const icon = document.getElementById('videoPlayIcon');
        const text = document.getElementById('videoPlayText');
        if (!icon || !text) return;

        if (state.isVideoPlaying) {
            icon.className = 'bi bi-pause-fill';
            text.textContent = '暂停视频';
        } else {
            icon.className = 'bi bi-play-fill';
            text.textContent = '播放视频';
        }
    }

    function updateVideoTimeDisplay() {
        if (!state.videoElement) return;

        const startTime = Number(analysisData.videoInfo.startTime || 0);
        const endTime = Number(analysisData.videoInfo.endTime || analysisData.videoInfo.duration || 0);
        const current = Math.max(0, state.videoElement.currentTime - startTime);
        const total = Math.max(0, endTime - startTime);

        const timeEl = document.getElementById('videoTime');
        if (timeEl) timeEl.textContent = `时间: ${current.toFixed(1)}s / ${total.toFixed(1)}s`;

        const slider = document.getElementById('videoTimeSlider');
        if (slider) {
            const progress = total > 0 ? (current / total) * 100 : 0;
            slider.value = progress;
        }
    }

    function startVideoFrameLoop() {
        if (state.isVideoLoopRendering) return;
        state.isVideoLoopRendering = true;

        function loop() {
            if (!state.isVideoPlaying) {
                state.isVideoLoopRendering = false;
                drawVideoFrame();
                return;
            }

            drawVideoFrame();
            updateVideoTimeDisplay();
            requestAnimationFrame(loop);
        }

        requestAnimationFrame(loop);
    }

    function initVideo() {
        if (state.videoInitialized) return;

        state.videoElement = document.getElementById('originalVideoSource');
        state.videoCanvas = document.getElementById('videoCanvas');
        if (!state.videoElement || !state.videoCanvas) return;

        state.videoContext = state.videoCanvas.getContext('2d');
        state.framesData = analysisData.poseData || [];

        const startTime = Number(analysisData.videoInfo.startTime || 0);

        state.videoElement.muted = true;
        state.videoElement.playsInline = true;
        state.videoElement.preload = 'auto';

        const toggleOverlayEl = document.getElementById('toggleOverlay');
        if (toggleOverlayEl) {
            state.showOverlay = toggleOverlayEl.checked;
            toggleOverlayEl.addEventListener('change', function () {
                state.showOverlay = this.checked;
                drawVideoFrame();
            });
        }

        state.videoElement.addEventListener('loadedmetadata', function () {
            resizeVideoCanvas();
            updateVideoTimeDisplay();
        });

        state.videoElement.addEventListener('loadeddata', function () {
            resizeVideoCanvas();
            try {
                state.videoElement.currentTime = Math.max(startTime, 0.01);
            } catch (e) {
                console.error('设置视频初始时间失败:', e);
            }
            drawVideoFrame();
        });

        state.videoElement.addEventListener('seeked', function () {
            drawVideoFrame();
            updateVideoTimeDisplay();
        });

        state.videoElement.addEventListener('play', function () {
            state.isVideoPlaying = true;
            updateVideoPlayButton();
            startVideoFrameLoop();
        });

        state.videoElement.addEventListener('pause', function () {
            state.isVideoPlaying = false;
            updateVideoPlayButton();
        });

        state.videoElement.addEventListener('ended', function () {
            state.isVideoPlaying = false;
            updateVideoPlayButton();
        });

        state.videoElement.addEventListener('timeupdate', function () {
            const endTime = Number(analysisData.videoInfo.endTime || analysisData.videoInfo.duration || 0);
            if (state.videoElement.currentTime > endTime) {
                state.videoElement.currentTime = startTime;
                state.videoElement.pause();
                state.isVideoPlaying = false;
                updateVideoPlayButton();
                drawVideoFrame();
                return;
            }
            updateVideoTimeDisplay();
        });

        state.videoElement.addEventListener('error', function () {
            console.error('视频加载失败:', state.videoElement.currentSrc, state.videoElement.error);
        });

        window.addEventListener('resize', resizeVideoCanvas);

        const videoTimeSlider = document.getElementById('videoTimeSlider');
        if (videoTimeSlider) {
            videoTimeSlider.addEventListener('input', (e) => {
                const endTime = Number(analysisData.videoInfo.endTime || analysisData.videoInfo.duration || 0);
                const duration = Math.max(endTime - startTime, 0.001);
                const newTime = startTime + (duration * Number(e.target.value) / 100);
                state.videoElement.currentTime = newTime;
            });
        }

        const videoSpeedSlider = document.getElementById('videoSpeedSlider');
        if (videoSpeedSlider) {
            videoSpeedSlider.addEventListener('input', function (e) {
                const option = state.speedOptions.find(opt => Number(opt.value) === Number(e.target.value)) || state.speedOptions[3];
                state.videoElement.playbackRate = option.speed;
                const valueEl = document.getElementById('videoSpeedValue');
                if (valueEl) valueEl.textContent = option.label;
            });
        }

        state.videoElement.load();
        state.videoInitialized = true;
    }

    function toggleVideoPlayback() {
        if (!state.videoInitialized) initVideo();
        if (!state.videoElement) return;

        if (state.videoElement.paused) {
            state.videoElement.play().catch(err => {
                console.error('视频播放失败:', err);
            });
        } else {
            state.videoElement.pause();
        }
    }

    window.ResultsVideo = {
        initVideo,
        drawVideoFrame,
        resizeVideoCanvas
    };

    window.toggleVideoPlayback = toggleVideoPlayback;
})();