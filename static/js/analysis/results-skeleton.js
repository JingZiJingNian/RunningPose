(function () {
    const state = window.ResultsState;

    function createSkeleton(frameData) {
        if (!state.scene) return;

        if (state.skeleton) {
            state.scene.remove(state.skeleton);
        }

        state.skeleton = new THREE.Group();

        if (!frameData || !frameData.landmarks_3d || frameData.landmarks_3d.length === 0) {
            return;
        }

        const landmarks = frameData.landmarks_3d;
        const connections = [
            [0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],
            [9,10],[11,12],[11,23],[12,24],[23,24],
            [11,13],[13,15],[15,17],[15,19],[15,21],[17,19],
            [12,14],[14,16],[16,18],[16,20],[16,22],[18,20],
            [23,25],[25,27],[27,29],[29,31],[27,31],
            [24,26],[26,28],[28,30],[30,32],[28,32]
        ];

        const jointGeometry = new THREE.SphereGeometry(0.045, 10, 10);
        const jointMaterial = new THREE.MeshPhongMaterial({
            color: 0x38bdf8,
            emissive: 0x1d4ed8,
            shininess: 60
        });

        landmarks.forEach((landmark) => {
            if (landmark.visibility === undefined || landmark.visibility > 0.1) {
                const joint = new THREE.Mesh(jointGeometry, jointMaterial);
                joint.position.set(landmark.x * 2, -landmark.y * 2, landmark.z * 2);
                state.skeleton.add(joint);
            }
        });

        const lineMaterial = new THREE.LineBasicMaterial({ color: 0x818cf8 });

        connections.forEach(([startIdx, endIdx]) => {
            const start = landmarks[startIdx];
            const end = landmarks[endIdx];

            if (!start || !end) return;
            if ((start.visibility !== undefined && start.visibility <= 0.1) ||
                (end.visibility !== undefined && end.visibility <= 0.1)) return;

            const points = [
                new THREE.Vector3(start.x * 2, -start.y * 2, start.z * 2),
                new THREE.Vector3(end.x * 2, -end.y * 2, end.z * 2)
            ];

            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const line = new THREE.Line(geometry, lineMaterial);
            state.skeleton.add(line);
        });

        state.scene.add(state.skeleton);
    }

    function updateSkeletonToFrame(frameIndex) {
        if (!state.framesData.length) return;
        const frameData = state.framesData[frameIndex];
        if (!frameData) return;
        createSkeleton(frameData);
    }

    function initOrbitControls() {
        if (!state.renderer || !state.camera) return;
        if (typeof THREE === 'undefined' || typeof THREE.OrbitControls !== 'function') {
            console.error('OrbitControls 加载失败');
            return;
        }

        state.controls = new THREE.OrbitControls(state.camera, state.renderer.domElement);
        state.controls.enableDamping = true;
        state.controls.dampingFactor = 0.08;
        state.controls.minDistance = 2;
        state.controls.maxDistance = 10;
        state.controls.target.set(0, 1, 0);
        state.controls.update();
    }

    function updateFrameDisplay() {
        const frameInfo = document.getElementById('frameInfo');
        if (frameInfo) {
            frameInfo.textContent = `帧: ${state.currentSkeletonFrameIndex + 1} / ${state.framesData.length || 0}`;
        }
    }

    function initFrameControls() {
        const frameSlider = document.getElementById('frameSlider');
        if (!frameSlider) return;

        frameSlider.max = Math.max(state.framesData.length - 1, 0);
        frameSlider.value = 0;

        frameSlider.addEventListener('input', function () {
            state.currentSkeletonFrameIndex = Number(this.value);
            updateSkeletonToFrame(state.currentSkeletonFrameIndex);
            updateFrameDisplay();
        });

        updateFrameDisplay();
    }

    function initSpeedControls() {
        const speedSlider = document.getElementById('speedSlider');
        const speedValue = document.getElementById('speedValue');
        if (!speedSlider || !speedValue) return;

        speedSlider.value = 3;
        speedValue.textContent = '1.0x';

        speedSlider.addEventListener('input', function () {
            const option = state.speedOptions.find(opt => Number(opt.value) === Number(this.value)) || state.speedOptions[3];
            state.skeletonSpeed = option.speed;
            speedValue.textContent = option.label;
        });
    }

    function toggleSkeletonPlayback() {
        state.isSkeletonAnimating = !state.isSkeletonAnimating;

        const icon = document.getElementById('skeletonPlayIcon');
        const text = document.getElementById('skeletonPlayText');
        if (!icon || !text) return;

        if (state.isSkeletonAnimating) {
            icon.className = 'bi bi-pause-fill';
            text.textContent = '暂停骨架';
        } else {
            icon.className = 'bi bi-play-fill';
            text.textContent = '播放骨架';
        }
    }

    function animate3DLoop(timestamp = 0) {
        state.animationFrameId = requestAnimationFrame(animate3DLoop);

        if (state.isSkeletonAnimating && state.framesData.length > 0) {
            const fps = Number(analysisData.videoInfo.fps || 30);
            const frameDuration = 1000 / (fps * state.skeletonSpeed);

            if (timestamp - state.lastSkeletonAnimationTime >= frameDuration) {
                state.currentSkeletonFrameIndex = (state.currentSkeletonFrameIndex + 1) % state.framesData.length;
                updateSkeletonToFrame(state.currentSkeletonFrameIndex);

                const frameSlider = document.getElementById('frameSlider');
                if (frameSlider) frameSlider.value = state.currentSkeletonFrameIndex;

                updateFrameDisplay();
                state.lastSkeletonAnimationTime = timestamp;
            }
        }

        if (state.controls) state.controls.update();
        if (state.renderer && state.scene && state.camera) state.renderer.render(state.scene, state.camera);
    }

    function resetCameraView() {
        if (!state.camera || !state.controls) return;
        state.camera.position.set(0, 1.4, 4.8);
        state.controls.target.set(0, 1, 0);
        state.controls.update();
    }

    function onWindowResize() {
        const container = document.querySelector('.canvas-container');
        if (container && state.camera && state.renderer) {
            const width = container.clientWidth;
            const height = container.clientHeight;
            state.camera.aspect = width / height;
            state.camera.updateProjectionMatrix();
            state.renderer.setSize(width, height);
        }

        if (window.ResultsVideo?.resizeVideoCanvas) {
            window.ResultsVideo.resizeVideoCanvas();
        }
    }

    function init3DScene() {
        const canvas = document.getElementById('skeletonCanvas');
        const loadingOverlay = document.getElementById('skeletonLoading');
        if (!canvas || !loadingOverlay) return;

        state.framesData = analysisData.poseData || [];

        if (!state.framesData.length) {
            loadingOverlay.innerHTML = `
                <div class="text-center">
                    <i class="bi bi-exclamation-triangle display-4 text-warning mb-3"></i>
                    <p class="mb-1">暂无 3D 骨架数据</p>
                    <small class="text-white-50">分析结果中没有可用的姿态关键点</small>
                </div>
            `;
            return;
        }

        try {
            const firstFrame = state.framesData[0];
            if (!firstFrame.landmarks_3d || !firstFrame.landmarks_3d.length) {
                throw new Error('姿态数据中没有 3D 关节点信息');
            }

            const container = document.querySelector('.canvas-container');
            const width = container.clientWidth;
            const height = container.clientHeight;

            state.scene = new THREE.Scene();
            state.scene.background = new THREE.Color(0x0b1220);

            state.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
            state.camera.position.set(0, 1.4, 4.8);
            state.camera.lookAt(0, 1, 0);

            state.renderer = new THREE.WebGLRenderer({
                canvas: canvas,
                antialias: true,
                alpha: true
            });
            state.renderer.setSize(width, height);
            state.renderer.setPixelRatio(window.devicePixelRatio);

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
            state.scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.95);
            directionalLight.position.set(4, 8, 6);
            state.scene.add(directionalLight);

            const backLight = new THREE.DirectionalLight(0x60a5fa, 0.45);
            backLight.position.set(-4, 6, -5);
            state.scene.add(backLight);

            const gridHelper = new THREE.GridHelper(10, 12, 0x334155, 0x1e293b);
            state.scene.add(gridHelper);

            const axesHelper = new THREE.AxesHelper(1.5);
            state.scene.add(axesHelper);

            createSkeleton(firstFrame);
            initOrbitControls();
            initFrameControls();
            initSpeedControls();
            animate3DLoop();

            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 300);

            window.addEventListener('resize', onWindowResize);

        } catch (error) {
            console.error('3D 场景初始化失败:', error);
            loadingOverlay.innerHTML = `
                <div class="text-center">
                    <i class="bi bi-exclamation-triangle display-4 text-danger mb-3"></i>
                    <p class="mb-1">3D 可视化初始化失败</p>
                    <small class="text-white-50">${window.ResultsUtils.escapeHtml(error.message)}</small>
                </div>
            `;
        }
    }

    window.ResultsSkeleton = {
        init3DScene
    };

    window.toggleSkeletonPlayback = toggleSkeletonPlayback;
    window.resetCameraView = resetCameraView;
})();