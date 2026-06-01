(function () {
    const getMetricValue = window.ResultsUtils.getMetricValue;
    const getMetricUnit = window.ResultsUtils.getMetricUnit;
    const getMetricConfidence = window.ResultsUtils.getMetricConfidence;
    const formatConfidence = window.ResultsUtils.formatConfidence;
    const escapeHtml = window.ResultsUtils.escapeHtml;

    const metricMeta = {
        cadence: {
            label: '步频',
            icon: 'bi-lightning-charge-fill',
            unitFallback: 'spm',
            description: '反映跑步节奏是否轻快稳定。步频偏低时，通常更容易出现前伸落脚和支撑拖沓。',
            judge: (v) => v == null ? ['暂无数据', 'flag-neutral'] : v < 155 ? ['偏低', 'flag-warn'] : v <= 185 ? ['较稳', 'flag-good'] : v <= 195 ? ['偏高', 'flag-neutral'] : ['较高', 'flag-warn']
        },
        ground_contact_time: {
            label: '触地时间',
            icon: 'bi-stopwatch-fill',
            unitFallback: 'ms',
            description: '反映单步支撑是否拖沓。触地时间偏长时，往往意味着回弹效率还有提升空间。',
            judge: (v) => v == null ? ['暂无数据', 'flag-neutral'] : v < 220 ? ['较短', 'flag-good'] : v <= 280 ? ['正常', 'flag-good'] : v <= 320 ? ['偏长', 'flag-warn'] : ['较长', 'flag-bad']
        },
        flight_time: {
            label: '腾空时间',
            icon: 'bi-arrow-up-right-circle-fill',
            unitFallback: 'ms',
            description: '反映离地到下一次触地之间的时间，应结合步频和触地时间一起理解。',
            judge: (v) => v == null ? ['暂无数据', 'flag-neutral'] : v < 60 ? ['较短', 'flag-neutral'] : v <= 140 ? ['合理', 'flag-good'] : ['较长', 'flag-neutral']
        },
        vertical_oscillation_rel: {
            label: '垂直振幅',
            icon: 'bi-graph-up-arrow',
            unitFallback: 'body_scale',
            description: '反映身体上下起伏是否偏大。起伏越明显，越可能带来额外能量浪费。',
            judge: (v) => v == null ? ['暂无数据', 'flag-neutral'] : v < 0.08 ? ['偏小', 'flag-neutral'] : v <= 0.14 ? ['较稳', 'flag-good'] : v <= 0.18 ? ['偏大', 'flag-warn'] : ['较大', 'flag-bad']
        },
        trunk_lean_angle: {
            label: '躯干前倾角',
            icon: 'bi-person-lines-fill',
            unitFallback: 'deg',
            description: '反映上身前倾是否自然稳定。关键不是越前倾越好，而是避免折腰式前倾。',
            judge: (v) => v == null ? ['暂无数据', 'flag-neutral'] : v < 5 ? ['偏直立', 'flag-neutral'] : v <= 13 ? ['较稳', 'flag-good'] : v <= 18 ? ['偏大', 'flag-warn'] : ['过大', 'flag-bad']
        },
        overstride_index: {
            label: '过度跨步指数',
            icon: 'bi-signpost-split-fill',
            unitFallback: 'leg_scale',
            description: '反映落脚点是否过于落在身体前方。指数越大，越提示存在前伸落脚倾向。',
            judge: (v) => v == null ? ['暂无数据', 'flag-neutral'] : v < 0.18 ? ['较紧凑', 'flag-good'] : v <= 0.30 ? ['可接受', 'flag-good'] : v <= 0.38 ? ['偏大', 'flag-warn'] : ['较大', 'flag-bad']
        }
    };

    function formatMetricValue(key, value) {
        if (value === null || value === undefined || Number.isNaN(value)) return '--';
        if (key === 'vertical_oscillation_rel' || key === 'overstride_index') return Number(value).toFixed(3);
        return Number(value).toFixed(1);
    }

    function buildSummaryHeadline() {
        const cadence = getMetricValue('cadence');
        const gct = getMetricValue('ground_contact_time');
        const trunk = getMetricValue('trunk_lean_angle');
        const osi = getMetricValue('overstride_index');

        const problems = [];
        if (cadence !== null && cadence < 155) problems.push('步频偏低');
        if (gct !== null && gct > 290) problems.push('触地时间偏长');
        if (trunk !== null && trunk > 16) problems.push('上身前倾偏大');
        if (osi !== null && osi > 0.32) problems.push('前伸落脚倾向');

        if (!problems.length) {
            return {
                title: '本次跑姿整体较稳定',
                body: '从本次分析结果看，你的步态节奏、支撑时间和身体控制整体较为稳定。后续更适合做细节优化，而不是进行大幅调整。'
            };
        }

        return {
            title: '本次跑姿存在明确的优先改进方向',
            body: `当前最值得优先关注的问题包括：${problems.join('、')}。建议先处理高优先级问题，再结合图表和动作复核进一步确认细节。`
        };
    }

    window.ResultsMetrics = {
        renderMetricCards() {
            const keys = ['cadence', 'ground_contact_time', 'flight_time', 'vertical_oscillation_rel', 'trunk_lean_angle', 'overstride_index'];
            const container = document.getElementById('metricsGrid');
            if (!container) return;
            container.innerHTML = '';

            keys.forEach((key) => {
                const meta = metricMeta[key];
                const value = getMetricValue(key);
                const unit = getMetricUnit(key, meta.unitFallback);
                const confidence = getMetricConfidence(key);
                const [judgeText, judgeClass] = meta.judge(value);

                const card = document.createElement('div');
                card.className = 'metric-card';
                card.innerHTML = `
                    <div>
                        <div class="metric-top">
                            <div>
                                <div class="metric-name">${meta.label}</div>
                                <div class="metric-value">
                                    ${formatMetricValue(key, value)}
                                    <span class="metric-unit">${unit}</span>
                                </div>
                            </div>
                            <div class="metric-icon"><i class="bi ${meta.icon}"></i></div>
                        </div>
                        <div class="metric-desc">${meta.description}</div>
                    </div>
                    <div class="metric-foot">
                        <span class="confidence-pill">${formatConfidence(confidence)}</span>
                        <span class="metric-flag ${judgeClass}">${judgeText}</span>
                    </div>
                `;
                container.appendChild(card);
            });
        },

        renderSummary() {
            const summary = buildSummaryHeadline();
            const quality = analysisData.overallMetrics?.analysis_quality || 'fair';
            const eventConf = Number(analysisData.overallMetrics?.event_summary?.event_confidence || 0);
            const es = analysisData.overallMetrics?.event_summary || {};
            const issueCount = Array.isArray(analysisData.issues) ? analysisData.issues.length : 0;

            const qualityTextMap = { good: '结果可信度较高', fair: '结果可信度中等', low: '结果可信度较低' };

            const headlineEl = document.getElementById('summaryHeadline');
            const bodyEl = document.getElementById('summaryBody');
            const heroEl = document.getElementById('heroSummaryText');
            const badge = document.getElementById('qualityBadge');
            const fill = document.getElementById('qualityConfidenceFill');
            const text = document.getElementById('qualityConfidenceText');
            const eventSummaryText = document.getElementById('eventSummaryText');

            if (headlineEl) headlineEl.textContent = summary.title;
            if (bodyEl) bodyEl.textContent = summary.body;
            if (heroEl) heroEl.textContent = summary.body;

            if (badge) {
                badge.className = 'quality-badge ' + (quality === 'good' ? 'quality-good' : quality === 'low' ? 'quality-low' : 'quality-fair');
                badge.innerHTML = `<i class="bi bi-bar-chart-line"></i><span>${qualityTextMap[quality] || '评估中'}</span>`;
            }

            if (fill) fill.style.width = `${Math.round(eventConf * 100)}%`;
            if (text) text.textContent = `${Math.round(eventConf * 100)}%`;
            if (eventSummaryText) {
                eventSummaryText.textContent = `本次识别到左脚初始触地 ${es.left_ic_count || 0} 次、右脚初始触地 ${es.right_ic_count || 0} 次，共输出 ${issueCount} 条主要诊断结果。`;
            }

            const totalStepsEl = document.getElementById('miniTotalSteps');
            const issueCountEl = document.getElementById('miniIssueCount');
            const icCountsEl = document.getElementById('miniIcCounts');
            const toCountsEl = document.getElementById('miniToCounts');

            if (totalStepsEl) totalStepsEl.textContent = analysisData.overallMetrics?.cadence?.total_steps ?? '--';
            if (issueCountEl) issueCountEl.textContent = issueCount;
            if (icCountsEl) icCountsEl.textContent = `${es.left_ic_count || 0} / ${es.right_ic_count || 0}`;
            if (toCountsEl) toCountsEl.textContent = `${es.left_to_count || 0} / ${es.right_to_count || 0}`;
        },

        renderIssues() {
            const container = document.getElementById('issuesList');
            if (!container) return;

            const issues = Array.isArray(analysisData.issues) ? analysisData.issues : [];
            if (!issues.length) {
                container.innerHTML = `
                    <div class="issue-card low">
                        <div class="issue-head">
                            <div>
                                <div class="issue-title">未发现明确的高优先级问题</div>
                                <div class="issue-meta">本次结果更适合做维持与微调</div>
                            </div>
                            <span class="issue-badge low">低风险</span>
                        </div>
                        <div class="issue-body">当前没有识别出高置信度且高优先级的问题。建议继续保持训练节奏，并在相同拍摄条件下定期复测，观察趋势变化。</div>
                        <div class="issue-suggestion"><strong>建议：</strong> 可以把重点放在节奏稳定性、落脚位置和左右侧动作一致性的长期对比上。</div>
                    </div>
                `;
                return;
            }

            container.innerHTML = issues.map((rawIssue) => {
                const issue = rawIssue || {};
                const sev = ['high', 'medium', 'low'].includes(issue.severity) ? issue.severity : 'low';
                const confValue = Number(issue.confidence);
                const conf = Number.isFinite(confValue) ? `${Math.round(confValue * 100)}%` : '--';

                return `
                    <div class="issue-card ${sev}">
                        <div class="issue-head">
                            <div>
                                <div class="issue-title">${escapeHtml(issue.message || '姿态提示')}</div>
                                <div class="issue-meta">
                                    <span><i class="bi bi-shield-check"></i> 置信度 ${conf}</span>
                                    <span><i class="bi bi-exclamation-circle"></i> ${sev === 'high' ? '高优先级' : sev === 'medium' ? '中优先级' : '低优先级'}</span>
                                </div>
                            </div>
                            <span class="issue-badge ${sev}">${sev === 'high' ? '建议优先处理' : sev === 'medium' ? '建议关注' : '建议观察'}</span>
                        </div>
                        <div class="issue-body">${escapeHtml(issue.message || '')}</div>
                        <div class="issue-suggestion"><strong>建议：</strong> ${escapeHtml(issue.suggestion || '结合视频和骨架进一步观察。')}</div>
                    </div>
                `;
            }).join('');
        },

        renderQuickNotes() {
            const cadence = getMetricValue('cadence');
            const gct = getMetricValue('ground_contact_time');
            const flight = getMetricValue('flight_time');
            const trunk = getMetricValue('trunk_lean_angle');
            const osi = getMetricValue('overstride_index');

            const notes = [];

            if (cadence !== null) {
                notes.push(cadence < 155
                    ? { title: '优先优化步态节奏', text: `当前步频约为 ${cadence.toFixed(1)} spm，整体节奏偏低。建议先从更轻、更快、更紧凑的落脚节奏入手，而不是主动迈更大步。` }
                    : { title: '保持节奏稳定性', text: `当前步频约为 ${cadence.toFixed(1)} spm，整体节奏处于相对可控范围。后续更适合结合触地时间和落脚方式做细节优化。` });
            }

            if (gct !== null && flight !== null) {
                notes.push({
                    title: '关注支撑与回弹效率',
                    text: `本次触地时间约 ${gct.toFixed(1)} ms，腾空时间约 ${flight.toFixed(1)} ms。建议结合这两项一起判断步态是否存在支撑拖沓、回弹不足的问题。`
                });
            }

            if (trunk !== null) {
                notes.push({
                    title: '保持上身姿态自然稳定',
                    text: `当前躯干前倾角约 ${trunk.toFixed(1)}°。关键不是一味增加前倾，而是避免折腰式前倾，让身体推进来自整体姿态与髋部驱动。`
                });
            }

            if (osi !== null) {
                notes.push({
                    title: '优化落脚位置',
                    text: `当前过度跨步指数约 ${osi.toFixed(3)}。如果落脚点过于落在身体前方，通常会增加支撑拖沓和节奏不稳的风险。`
                });
            }

            const container = document.getElementById('quickNotes');
            if (!container) return;

            container.innerHTML = notes.map(note => `
                <div class="note-card">
                    <h6>${escapeHtml(note.title)}</h6>
                    <p>${escapeHtml(note.text)}</p>
                </div>
            `).join('');
        }
    };
})();