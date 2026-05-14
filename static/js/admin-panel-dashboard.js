(function () {
    function readJson(id) {
        var el = document.getElementById(id);
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return null;
        }
    }

    var sales = readJson('ap-sales-data');
    var makes = readJson('ap-makes-data');

    if (typeof Chart === 'undefined') return;

    Chart.defaults.font.family = '"Inter Tight", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    Chart.defaults.color = '#6b7280';

    if (sales) {
        var salesCanvas = document.getElementById('ap-sales-chart');
        if (salesCanvas) {
            new Chart(salesCanvas, {
                type: 'bar',
                data: {
                    labels: sales.labels || [],
                    datasets: [
                        {
                            label: 'Monthly target',
                            data: sales.target || [],
                            backgroundColor: '#e6e8ec',
                            borderRadius: 4,
                            barThickness: 14,
                            order: 2,
                        },
                        {
                            label: 'Cars sold',
                            data: sales.sold || [],
                            backgroundColor: '#2563eb',
                            borderRadius: 4,
                            barThickness: 14,
                            order: 1,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#fff',
                            borderColor: '#e6e8ec',
                            borderWidth: 1,
                            titleColor: '#1a1f29',
                            bodyColor: '#6b7280',
                            padding: 10,
                        },
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            border: { display: false },
                            ticks: { color: '#6b7280', font: { size: 12 } },
                        },
                        y: {
                            grid: { color: '#eef0f3', drawBorder: false },
                            border: { display: false },
                            ticks: { color: '#97a0ad', font: { size: 11 }, padding: 4 },
                            beginAtZero: true,
                        },
                    },
                },
            });
        }
    }

    if (makes) {
        var makesCanvas = document.getElementById('ap-makes-chart');
        var totalEl = document.getElementById('ap-makes-total');
        var subEl = document.getElementById('ap-makes-sub');
        var legendEl = document.getElementById('ap-makes-legend');

        if (totalEl) totalEl.textContent = makes.total || 0;
        if (subEl) {
            var n = makes.make_count || (makes.labels ? makes.labels.length : 0);
            subEl.textContent = n === 1 ? 'across 1 make' : 'across ' + n + ' makes';
        }

        if (legendEl && makes.labels && makes.values) {
            var total = makes.total || 0;
            legendEl.innerHTML = makes.labels.map(function (name, i) {
                var val = makes.values[i] || 0;
                var pct = total ? ((val / total) * 100).toFixed(1) : '0.0';
                var color = (makes.colors && makes.colors[i]) || '#2563eb';
                return (
                    '<div class="legend-row">' +
                    '<span class="legend-sw" style="background:' + color + '"></span>' +
                    '<span class="legend-name">' + name + '</span>' +
                    '<span class="legend-val num">' + val + ' units</span>' +
                    '<span class="legend-pct num">' + pct + '%</span>' +
                    '</div>'
                );
            }).join('');
        }

        if (makesCanvas && makes.labels && makes.labels.length) {
            new Chart(makesCanvas, {
                type: 'doughnut',
                data: {
                    labels: makes.labels,
                    datasets: [{
                        data: makes.values,
                        backgroundColor: makes.colors || ['#2563eb'],
                        borderWidth: 0,
                        spacing: 2,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '68%',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#fff',
                            borderColor: '#e6e8ec',
                            borderWidth: 1,
                            titleColor: '#1a1f29',
                            bodyColor: '#6b7280',
                        },
                    },
                },
            });
        }
    }
})();
