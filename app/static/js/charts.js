/**
 * 钢筋精细化管理平台 — 图表统一封装
 * 依赖：Chart.js（已在 base.html 中加载）
 */
(function () {
    "use strict";

    // 项目统一配色（与 style.css :root 令牌对齐）
    var COLORS = [
        "#1a2744", "#f15a24", "#0098ae", "#198754",
        "#f0a020", "#dc3545", "#6f42c1", "#20c997"
    ];

    function getColors(count) {
        var result = [];
        for (var i = 0; i < count; i++) {
            result.push(COLORS[i % COLORS.length]);
        }
        return result;
    }

    function getCanvas(canvasId) {
        var el = document.getElementById(canvasId);
        return el ? el.getContext("2d") : null;
    }

    function commonOptions(options) {
        options = options || {};
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: options.legendPosition || "bottom",
                    labels: { font: { size: 12 } }
                }
            }
        };
    }

    window.RebarCharts = {
        /**
         * 柱状图
         * @param {string} canvasId
         * @param {Array} labels
         * @param {Array} datasets - Chart.js dataset 数组
         * @param {Object} options
         */
        renderBarChart: function (canvasId, labels, datasets, options) {
            var ctx = getCanvas(canvasId);
            if (!ctx) return null;
            options = options || {};
            return new Chart(ctx, {
                type: "bar",
                data: { labels: labels, datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, title: { display: !!options.yTitle, text: options.yTitle } }
                    },
                    plugins: {
                        legend: { position: options.legendPosition || "top" },
                        title: options.title ? { display: true, text: options.title } : undefined
                    }
                }
            });
        },

        /**
         * 饼图
         */
        renderPieChart: function (canvasId, labels, data, options) {
            var ctx = getCanvas(canvasId);
            if (!ctx) return null;
            options = options || {};
            return new Chart(ctx, {
                type: "pie",
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: getColors(data.length)
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: options.legendPosition || "bottom" },
                        title: options.title ? { display: true, text: options.title } : undefined,
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    var suffix = options.suffix || "";
                                    return context.label + ": " + context.raw + suffix;
                                }
                            }
                        }
                    }
                }
            });
        },

        /**
         * 环形图
         */
        renderDoughnutChart: function (canvasId, labels, data, options) {
            var ctx = getCanvas(canvasId);
            if (!ctx) return null;
            options = options || {};
            return new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: getColors(data.length)
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: options.legendPosition || "bottom" },
                        title: options.title ? { display: true, text: options.title } : undefined,
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    var suffix = options.suffix || "";
                                    return context.label + ": " + context.raw + suffix;
                                }
                            }
                        }
                    }
                }
            });
        },

        /**
         * 折线图
         */
        renderLineChart: function (canvasId, labels, datasets, options) {
            var ctx = getCanvas(canvasId);
            if (!ctx) return null;
            options = options || {};
            return new Chart(ctx, {
                type: "line",
                data: { labels: labels, datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, title: { display: !!options.yTitle, text: options.yTitle } }
                    },
                    plugins: {
                        legend: { position: options.legendPosition || "top" },
                        title: options.title ? { display: true, text: options.title } : undefined
                    }
                }
            });
        },

        /**
         * 雷达图
         */
        renderRadarChart: function (canvasId, labels, datasets, options) {
            var ctx = getCanvas(canvasId);
            if (!ctx) return null;
            options = options || {};
            return new Chart(ctx, {
                type: "radar",
                data: { labels: labels, datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            beginAtZero: true,
                            suggestedMax: options.suggestedMax
                        }
                    },
                    plugins: {
                        legend: { position: options.legendPosition || "bottom" },
                        title: options.title ? { display: true, text: options.title } : undefined
                    }
                }
            });
        },

        /**
         * 半圆环图（仪表盘效果）
         */
        renderSemiDoughnutChart: function (canvasId, labels, data, options) {
            var ctx = getCanvas(canvasId);
            if (!ctx) return null;
            options = options || {};
            return new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: options.colors || getColors(data.length),
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    rotation: -90,
                    circumference: 180,
                    cutout: "75%",
                    plugins: {
                        legend: { display: false },
                        title: options.title ? { display: true, text: options.title } : undefined,
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    var suffix = options.suffix || "";
                                    return context.label + ": " + context.raw + suffix;
                                }
                            }
                        }
                    }
                }
            });
        }
    };
})();
