(function () {
    const CHART_COLORS = [
        "#6f42c1",
        "#2563eb",
        "#14b8a6",
        "#f97316",
        "#ef4444",
        "#eab308",
        "#0f766e",
        "#7c3aed",
    ];

    function initListFilters() {
        document.querySelectorAll("[data-list-filter]").forEach((wrapper) => {
            const input = wrapper.querySelector("[data-list-search]");
            const items = Array.from(wrapper.querySelectorAll("[data-list-item]"));
            const count = wrapper.querySelector("[data-list-count]");
            const emptyState = wrapper.querySelector("[data-empty-state]");

            if (!input || !items.length || !count || !emptyState) {
                return;
            }

            const applyFilter = () => {
                const query = input.value.trim().toLowerCase();
                let visibleCount = 0;

                items.forEach((item) => {
                    const haystack = item.dataset.searchText || "";
                    const match = !query || haystack.includes(query);
                    item.classList.toggle("is-hidden", !match);
                    if (match) {
                        visibleCount += 1;
                    }
                });

                count.textContent = String(visibleCount);
                emptyState.classList.toggle("d-none", visibleCount !== 0);
            };

            input.addEventListener("input", applyFilter);
            applyFilter();
        });
    }

    function createCard(className, value, label, note) {
        const card = document.createElement("div");
        card.className = className;
        card.setAttribute("data-animate", "");
        card.innerHTML = "<strong></strong><span></span><small></small>";
        card.querySelector("strong").textContent = value;
        card.querySelector("span").textContent = label;
        card.querySelector("small").textContent = note || "";
        return card;
    }

    function renderTimeline(target, entries) {
        if (!target) {
            return;
        }

        target.innerHTML = "";
        if (!entries || !entries.length) {
            target.innerHTML = "<p class='text-secondary mb-0'>No activity recorded yet.</p>";
            return;
        }

        entries.forEach((entry) => {
            const item = document.createElement("article");
            item.className = "timeline-entry " + (entry.tone || "info");
            item.setAttribute("data-animate", "");
            item.innerHTML = [
                "<span class='timeline-date'></span>",
                "<span class='timeline-title'></span>",
                "<span class='timeline-meta'></span>",
            ].join("");
            item.querySelector(".timeline-date").textContent = entry.date;
            item.querySelector(".timeline-title").textContent = entry.title;
            item.querySelector(".timeline-meta").textContent = entry.meta;
            target.appendChild(item);
        });
    }

    function buildSelect(labelText, options, dataFilterId) {
        const wrapper = document.createElement("div");
        const label = document.createElement("label");
        const select = document.createElement("select");

        label.className = "form-label small text-secondary mb-1";
        label.textContent = labelText;
        select.className = "form-select";
        select.dataset.filterId = dataFilterId;

        options.forEach((optionConfig) => {
            const option = document.createElement("option");
            option.value = optionConfig.id;
            option.textContent = optionConfig.label;
            select.appendChild(option);
        });

        wrapper.appendChild(label);
        wrapper.appendChild(select);
        return wrapper;
    }

    function applyFilters(records, filterControls) {
        return records.filter((record) => {
            return filterControls.every((control) => {
                const value = control.value;
                const filterId = control.dataset.filterId;
                return value === "all" || record[filterId] === value;
            });
        });
    }

    function buildGroupedSeries(records, groupBy) {
        const groups = new Map();

        records.forEach((record) => {
            const key = record[groupBy] || "Not available";
            groups.set(key, (groups.get(key) || 0) + 1);
        });

        return Array.from(groups.entries())
            .sort((left, right) => right[1] - left[1])
            .slice(0, 6)
            .map((entry, index) => ({
                label: entry[0],
                value: entry[1],
                color: CHART_COLORS[index % CHART_COLORS.length],
            }));
    }

    function polarToCartesian(centerX, centerY, radius, angleInDegrees) {
        const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
        return {
            x: centerX + (radius * Math.cos(angleInRadians)),
            y: centerY + (radius * Math.sin(angleInRadians)),
        };
    }

    function describeArc(centerX, centerY, radius, startAngle, endAngle) {
        const start = polarToCartesian(centerX, centerY, radius, endAngle);
        const end = polarToCartesian(centerX, centerY, radius, startAngle);
        const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

        return [
            "M", start.x, start.y,
            "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y,
        ].join(" ");
    }

    function buildDonutSvg(series, total) {
        const center = 100;
        const radius = 62;
        let currentAngle = 0;

        const segments = series.map((item) => {
            const angle = (item.value / total) * 360;
            const path = describeArc(center, center, radius, currentAngle, currentAngle + angle);
            currentAngle += angle;
            const percentage = Math.round((item.value / total) * 100);
            return "<path d='" + path + "' stroke='" + item.color + "' stroke-width='34' fill='none' stroke-linecap='butt' data-segment-label='" + item.label + "' data-segment-value='" + item.value + "' data-segment-percentage='" + percentage + "'></path>";
        }).join("");

        return [
            "<svg class='donut-svg' viewBox='0 0 200 200' aria-hidden='true'>",
            "<circle cx='100' cy='100' r='" + radius + "' stroke='#e9eef8' stroke-width='34' fill='none'></circle>",
            segments,
            "<circle cx='100' cy='100' r='42' fill='white'></circle>",
            "<text x='100' y='96' text-anchor='middle' class='donut-total'>" + total + "</text>",
            "<text x='100' y='116' text-anchor='middle' class='donut-caption'>events</text>",
            "</svg>",
        ].join("");
    }

    function attachDonutTooltip(chartContainer) {
        const svg = chartContainer.querySelector(".donut-svg");
        if (!svg) {
            return;
        }

        let tooltip = chartContainer.querySelector(".donut-tooltip");
        if (!tooltip) {
            tooltip = document.createElement("div");
            tooltip.className = "donut-tooltip";
            chartContainer.appendChild(tooltip);
        }

        const segments = svg.querySelectorAll("[data-segment-label]");
        segments.forEach((segment) => {
            segment.addEventListener("mouseenter", (event) => {
                const label = event.target.dataset.segmentLabel;
                const value = event.target.dataset.segmentValue;
                const percentage = event.target.dataset.segmentPercentage;
                tooltip.innerHTML = "<strong>" + label + "</strong><span>" + value + " events (" + percentage + "%)</span>";
                tooltip.classList.add("is-visible");
            });

            segment.addEventListener("mousemove", (event) => {
                const bounds = chartContainer.getBoundingClientRect();
                tooltip.style.left = (event.clientX - bounds.left + 12) + "px";
                tooltip.style.top = (event.clientY - bounds.top + 12) + "px";
            });

            segment.addEventListener("mouseleave", () => {
                tooltip.classList.remove("is-visible");
            });
        });
    }

    function buildConicGradient(series) {
        const total = series.reduce((sum, item) => sum + item.value, 0) || 1;
        let current = 0;

        return "conic-gradient(" + series.map((item) => {
            const start = (current / total) * 360;
            current += item.value;
            const end = (current / total) * 360;
            return item.color + " " + start + "deg " + end + "deg";
        }).join(", ") + ")";
    }

    function summarizeFilters(filterControls) {
        const active = filterControls
            .filter((control) => control.value !== "all")
            .map((control) => {
                const label = control.closest("div").querySelector("label").textContent;
                const selected = control.options[control.selectedIndex].textContent;
                return label + ": " + selected;
            });

        return active.length ? active.join(" | ") : "No extra filters applied.";
    }

    function renderDonutChart(target, summaryTarget, chartConfig, groupBy, filterControls) {
        if (!target || !summaryTarget || !chartConfig) {
            return;
        }

        const filteredRecords = applyFilters(chartConfig.records || [], filterControls);
        const series = buildGroupedSeries(filteredRecords, groupBy);
        target.innerHTML = "";

        if (!series.length) {
            target.innerHTML = "<p class='text-secondary mb-0'>" + (chartConfig.emptyMessage || "No data.") + "</p>";
            summaryTarget.textContent = "No results for the selected filter set.";
            return;
        }

        const total = series.reduce((sum, item) => sum + item.value, 0);
        const visual = document.createElement("div");
        visual.className = "donut-layout";

        const donut = document.createElement("div");
        donut.className = "donut-chart";
        donut.setAttribute("data-animate", "");
        donut.innerHTML = buildDonutSvg(series, total);

        const legend = document.createElement("div");
        legend.className = "donut-legend";

        series.forEach((item) => {
            const percentage = Math.round((item.value / total) * 100);
            const row = document.createElement("div");
            row.className = "donut-legend-row";
            row.setAttribute("data-animate", "");
            row.innerHTML = [
                "<span class='donut-swatch'></span>",
                "<span class='donut-label'></span>",
                "<strong class='donut-value'></strong>",
            ].join("");
            row.querySelector(".donut-swatch").style.backgroundColor = item.color;
            row.querySelector(".donut-label").textContent = item.label;
            row.querySelector(".donut-value").textContent = item.value + " (" + percentage + "%)";
            legend.appendChild(row);
        });

        visual.appendChild(donut);
        visual.appendChild(legend);
        target.appendChild(visual);
        attachDonutTooltip(visual);
        summaryTarget.textContent = "Grouped by " + String(groupBy).replace(/_/g, " ") + ". " + summarizeFilters(filterControls);
    }

    function initDashboards() {
        document.querySelectorAll("[data-dashboard]").forEach((dashboard) => {
            const configId = dashboard.dataset.configId;
            const configNode = document.getElementById(configId);

            if (!configNode) {
                return;
            }

            const config = JSON.parse(configNode.textContent);
            const statGrid = dashboard.querySelector("[data-stat-grid]");
            const insightGrid = dashboard.querySelector("[data-insight-grid]");
            const timeline = dashboard.querySelector("[data-timeline]");
            const chart = dashboard.querySelector("[data-chart]");
            const chartSummary = dashboard.querySelector("[data-chart-summary]");
            const groupSelect = dashboard.querySelector("[data-chart-group]");
            const filterGrid = dashboard.querySelector("[data-filter-grid]");

            if (statGrid && Array.isArray(config.headlineStats)) {
                config.headlineStats.forEach((item) => {
                    statGrid.appendChild(createCard("dashboard-stat-card", item.value, item.label, item.note));
                });
            }

            if (insightGrid && Array.isArray(config.insights)) {
                config.insights.forEach((item) => {
                    insightGrid.appendChild(createCard("insight-card", item.value, item.label, ""));
                });
            }

            renderTimeline(timeline, config.timeline || []);

            if (chart && chartSummary && groupSelect && filterGrid && config.chart) {
                if (!groupSelect.options.length) {
                    (config.chart.groupOptions || []).forEach((group) => {
                        const option = document.createElement("option");
                        option.value = group.id;
                        option.textContent = group.label;
                        groupSelect.appendChild(option);
                    });
                }

                if (!groupSelect.value) {
                    groupSelect.value = config.chart.defaultGroup;
                }

                if (!filterGrid.querySelector("select")) {
                    (config.chart.filters || []).forEach((filterConfig) => {
                        const field = buildSelect(filterConfig.label, filterConfig.options, filterConfig.id);
                        filterGrid.appendChild(field);
                    });
                }

                const filterControls = Array.from(filterGrid.querySelectorAll("select"));
                const repaint = () => {
                    renderDonutChart(chart, chartSummary, config.chart, groupSelect.value, filterControls);
                    initRevealAnimations();
                };

                groupSelect.addEventListener("change", repaint);
                filterControls.forEach((control) => control.addEventListener("change", repaint));
                repaint();
            }
        });
    }

    let revealObserver;
    function initRevealAnimations() {
        const items = document.querySelectorAll("[data-animate]:not(.is-visible)");

        if (!("IntersectionObserver" in window)) {
            items.forEach((item) => item.classList.add("is-visible"));
            return;
        }

        if (!revealObserver) {
            revealObserver = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        revealObserver.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.15 });
        }

        items.forEach((item) => revealObserver.observe(item));
    }

    document.addEventListener("DOMContentLoaded", () => {
        initListFilters();
        initDashboards();
        initRevealAnimations();
    });
}());
