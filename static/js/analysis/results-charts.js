(function () {
    // 悬停十字准线
    const crosshairPlugin = {
        id: 'crosshairPlugin',
        afterDatasetsDraw(chart, args, pluginOptions) {
            const { ctx, chartArea, tooltip } = chart;
            if (!tooltip || !tooltip._active || !tooltip._active.length) return;

            const activePoint = tooltip._active[0];
            const x = activePoint.element.x;
            const y = activePoint.element.y;

            ctx.save();

            ctx.beginPath();
            ctx.setLineDash([4, 4]);
            ctx.lineWidth = 1;
            ctx.strokeStyle = pluginOptions?.lineColor || 'rgba(99, 102, 241, 0.9)';
            ctx.moveTo(x, chartArea.top);
            ctx.lineTo(x, chartArea.bottom);
            ctx.stroke();

            ctx.beginPath();
            ctx.setLineDash([4, 4]);
            ctx.lineWidth = 1;
            ctx.strokeStyle = pluginOptions?.lineColor || 'rgba(99, 102, 241, 0.9)';
            ctx.moveTo(chartArea.left, y);
            ctx.lineTo(chartArea.right, y);
            ctx.stroke();

            ctx.restore();
        }
    };

    // 均值水平虚线：不参与坐标缩放
    const meanLinePlugin = {
        id: 'meanLinePlugin',
        afterDraw(chart, args, pluginOptions) {
            if (!pluginOptions || pluginOptions.value === null || pluginOptions.value === undefined || Number.isNaN(pluginOptions.value)) {
                return;
            }

            const { ctx, chartArea, scales } = chart;
            const yScale = scales.y;
            if (!yScale) return;

            const yPixel = yScale.getPixelForValue(pluginOptions.value);
            if (!Number.isFinite(yPixel)) return;
            if (yPixel < chartArea.top || yPixel > chartArea.bottom) return;

            ctx.save();

            ctx.beginPath();
            ctx.setLineDash(pluginOptions.dash || [8, 6]);
            ctx.lineWidth = pluginOptions.lineWidth || 1.5;
            ctx.strokeStyle = pluginOptions.color || 'rgba(15, 23, 42, 0.65)';
            ctx.moveTo(chartArea.left, yPixel);
            ctx.lineTo(chartArea.right, yPixel);
            ctx.stroke();

            if (pluginOptions.label) {
                const labelText = `${pluginOptions.label}: ${Number(pluginOptions.value).toFixed(pluginOptions.decimals ?? 2)}${pluginOptions.suffix || ''}`;
                ctx.setLineDash([]);
                ctx.font = '12px sans-serif';
                ctx.fillStyle = pluginOptions.color || 'rgba(15, 23, 42, 0.65)';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'bottom';
                ctx.fillText(labelText, chartArea.right - 6, yPixel - 4);
            }

            ctx.restore();
        }
    };

    Chart.register(crosshairPlugin, meanLinePlugin);

    function buildVerticalGradient(ctx, chartArea, topColor, bottomColor) {
        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        gradient.addColorStop(0, topColor);
        gradient.addColorStop(1, bottomColor);
        return gradient;
    }

    function lineTooltipLabel(label, suffix = '', decimals = 4) {
        return function (context) {
            const x = context.parsed.x;
            const y = context.parsed.y;
            if (y === null || y === undefined) return `${label}: --`;
            return `${label}: ${Number(y).toFixed(decimals)}${suffix} @ ${Number(x).toFixed(2)}s`;
        };
    }

    function scatterTooltipLabel(label, decimals = 3) {
        return function (context) {
            const x = context.parsed.x;
            const y = context.parsed.y;
            return `${label}: ${Number(y).toFixed(decimals)} @ ${Number(x).toFixed(2)}s`;
        };
    }

    function buildWaveChart(canvasId, label, wave, yAxisText, colors, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !wave || !Array.isArray(wave.x) || !Array.isArray(wave.y) || !wave.x.length) return;

        const points = wave.x
            .map((x, i) => ({ x, y: wave.y[i] }))
            .filter(p => p.y !== null && p.y !== undefined && !Number.isNaN(p.y));

        if (!points.length) return;

        new Chart(canvas, {
            type: 'line',
            data: {
                datasets: [{
                    label,
                    data: points,
                    parsing: false,
                    borderColor: colors.line,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHitRadius: 16,
                    tension: 0.28,
                    fill: true,
                    backgroundColor(context) {
                        const { chart } = context;
                        const { ctx, chartArea } = chart;
                        if (!chartArea) return colors.fillTop;
                        return buildVerticalGradient(
                            ctx,
                            chartArea,
                            colors.fillTop,
                            colors.fillBottom
                        );
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                parsing: false,
                interaction: {
                    mode: 'nearest',
                    intersect: false,
                    axis: 'x'
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            usePointStyle: true,
                            boxWidth: 8
                        }
                    },
                    tooltip: {
                        enabled: true,
                        mode: 'nearest',
                        intersect: false,
                        callbacks: {
                            label: lineTooltipLabel(label, options.tooltipSuffix || '', options.tooltipDecimals ?? 4)
                        }
                    },
                    crosshairPlugin: {
                        lineColor: colors.crosshair
                    },
                    meanLinePlugin: options.meanLine || null
                },
                scales: {
                    x: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: '时间 (s)'
                        },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.15)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: yAxisText
                        },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.15)'
                        }
                    }
                }
            }
        });
    }

    function buildScatterChart(canvasId, label, color, points, yLabel, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !Array.isArray(points) || !points.length) return;

        new Chart(canvas, {
            type: 'scatter',
            data: {
                datasets: [{
                    label,
                    data: points,
                    backgroundColor: color,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                parsing: false,
                interaction: {
                    mode: 'nearest',
                    intersect: false
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: scatterTooltipLabel(label, options.tooltipDecimals ?? 3)
                        }
                    },
                    meanLinePlugin: options.meanLine || null
                },
                scales: {
                    x: {
                        type: 'linear',
                        title: { display: true, text: '时间 (s)' },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.15)'
                        }
                    },
                    y: {
                        title: { display: true, text: yLabel },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.15)'
                        }
                    }
                }
            }
        });
    }

    function meanOfScatter(points) {
        if (!Array.isArray(points) || !points.length) return null;
        const ys = points
            .map(p => Number(p.y))
            .filter(v => Number.isFinite(v));
        if (!ys.length) return null;
        return ys.reduce((a, b) => a + b, 0) / ys.length;
    }

    window.ResultsCharts = {
        renderMetricCharts() {
            const ts = analysisData.overallMetrics?.timeseries || {};

            const trunkMean = analysisData.overallMetrics?.trunk_lean_angle?.value ?? null;

            const cadenceScatter = ts.cadence_scatter || [];
            const strideScatter = ts.stride_length_scatter || [];
            const gctScatter = ts.ground_contact_time_scatter || [];
            const flightScatter = ts.flight_time_scatter || [];

            const cadenceMean = analysisData.overallMetrics?.cadence?.value ?? meanOfScatter(cadenceScatter);
            const strideMean = meanOfScatter(strideScatter);
            const gctMean = analysisData.overallMetrics?.ground_contact_time?.value ?? meanOfScatter(gctScatter);
            const flightMean = analysisData.overallMetrics?.flight_time?.value ?? meanOfScatter(flightScatter);

            // 1) 垂直振幅波形：不画摘要值虚线
            buildWaveChart(
                'verticalOscillationChart',
                '垂直振幅（相对量）',
                ts.vertical_oscillation_wave,
                '相对振幅',
                {
                    line: 'rgba(79, 70, 229, 1)',
                    fillTop: 'rgba(79, 70, 229, 0.30)',
                    fillBottom: 'rgba(79, 70, 229, 0.02)',
                    crosshair: 'rgba(79, 70, 229, 0.75)'
                },
                {
                    tooltipDecimals: 5
                }
            );

            // 2) 躯干前倾角波形：均值线用插件绘制，不参与坐标缩放
            buildWaveChart(
                'trunkLeanChart',
                '躯干前倾角',
                ts.trunk_lean_angle_wave,
                '角度 (deg)',
                {
                    line: 'rgba(14, 165, 233, 1)',
                    fillTop: 'rgba(14, 165, 233, 0.28)',
                    fillBottom: 'rgba(14, 165, 233, 0.02)',
                    crosshair: 'rgba(14, 165, 233, 0.75)'
                },
                {
                    tooltipSuffix: '°',
                    tooltipDecimals: 4,
                    meanLine: trunkMean !== null ? {
                        value: Number(trunkMean),
                        color: 'rgba(14, 165, 233, 0.95)',
                        label: '均值',
                        suffix: '°',
                        decimals: 2,
                        dash: [8, 6],
                        lineWidth: 1.5
                    } : null
                }
            );

            // 3) 四张散点图都加均值虚线
            buildScatterChart(
                'cadenceScatterChart',
                '步频',
                'rgba(16, 185, 129, 0.85)',
                cadenceScatter,
                '步频 (spm)',
                {
                    meanLine: cadenceMean !== null ? {
                        value: Number(cadenceMean),
                        color: 'rgba(16, 185, 129, 0.95)',
                        label: '均值',
                        decimals: 2,
                        dash: [8, 6],
                        lineWidth: 1.5
                    } : null
                }
            );

            buildScatterChart(
                'strideScatterChart',
                '步幅（相对量）',
                'rgba(245, 158, 11, 0.85)',
                strideScatter,
                '步幅 (relative)',
                {
                    meanLine: strideMean !== null ? {
                        value: Number(strideMean),
                        color: 'rgba(245, 158, 11, 0.95)',
                        label: '均值',
                        decimals: 4,
                        dash: [8, 6],
                        lineWidth: 1.5
                    } : null
                }
            );

            buildScatterChart(
                'gctScatterChart',
                '触地时间',
                'rgba(239, 68, 68, 0.85)',
                gctScatter,
                '触地时间 (ms)',
                {
                    meanLine: gctMean !== null ? {
                        value: Number(gctMean),
                        color: 'rgba(239, 68, 68, 0.95)',
                        label: '均值',
                        decimals: 2,
                        dash: [8, 6],
                        lineWidth: 1.5
                    } : null
                }
            );

            buildScatterChart(
                'flightScatterChart',
                '腾空时间',
                'rgba(99, 102, 241, 0.85)',
                flightScatter,
                '腾空时间 (ms)',
                {
                    meanLine: flightMean !== null ? {
                        value: Number(flightMean),
                        color: 'rgba(99, 102, 241, 0.95)',
                        label: '均值',
                        decimals: 2,
                        dash: [8, 6],
                        lineWidth: 1.5
                    } : null
                }
            );
        }
    };
})();