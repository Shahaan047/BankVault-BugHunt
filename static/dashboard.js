document.addEventListener("DOMContentLoaded", function () {

    // =====================================
    // CURRENT DATE
    // =====================================

    const dateElement = document.getElementById("currentDate");

    if (dateElement) {
        const today = new Date();

        dateElement.textContent = today.toLocaleDateString("en-IN", {
            day: "numeric",
            month: "short",
            year: "numeric"
        });
    }


    // =====================================
    // SIDEBAR COLLAPSE
    // =====================================

    const sidebar = document.getElementById("sidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const mainContent = document.querySelector(".main-content");

    function updateSidebarButton() {
        if (!sidebarToggle) return;

        const isExpanded = window.innerWidth <= 480
            ? sidebar.classList.contains("mobile-open")
            : !sidebar.classList.contains("collapsed");

        sidebarToggle.setAttribute("aria-expanded", String(isExpanded));
    }

    if (sidebar && sidebarToggle && mainContent) {

        sidebarToggle.addEventListener("click", function () {

            if (window.innerWidth <= 480) {

                sidebar.classList.toggle("mobile-open");

            } else {

                sidebar.classList.toggle("collapsed");

                mainContent.classList.toggle("sidebar-collapsed");

            }

            updateSidebarButton();

        });

        window.addEventListener("resize", function () {

            if (window.innerWidth > 480) {
                sidebar.classList.remove("mobile-open");
            }

            updateSidebarButton();

        });

    }


    // =====================================
    // TOAST NOTIFICATIONS
    // =====================================

    const toast = document.getElementById("toast");

    let toastTimeout;

    function showToast(message) {

        if (!toast) return;

        toast.textContent = message;

        toast.classList.add("show");

        clearTimeout(toastTimeout);

        toastTimeout = setTimeout(function () {
            toast.classList.remove("show");
        }, 3000);

    }


    // =====================================
    // DEMO ACTION BUTTONS
    // =====================================

    document.querySelectorAll("[data-action]").forEach(function (button) {

        button.addEventListener("click", function () {

            const action = button.dataset.action;

            showToast(
                action + " is part of the demo interface. " +
                "We can implement this feature in the next stage."
            );

        });

    });


    // =====================================
    // SIDEBAR NAVIGATION
    // =====================================

    document.querySelectorAll(".sidebar-link[href^='#']").forEach(
        function (link) {

            link.addEventListener("click", function () {

                document.querySelectorAll(".sidebar-link").forEach(
                    function (item) {
                        item.classList.remove("active");
                    }
                );

                link.classList.add("active");

                if (window.innerWidth <= 480 && sidebar) {
                    sidebar.classList.remove("mobile-open");
                    updateSidebarButton();
                }

            });

        }
    );


    // =====================================
    // FINANCIAL CHART
    // =====================================

    const chartCanvas = document.getElementById("financeChart");
    const chartPeriod = document.getElementById("chartPeriod");

    let financeChart = null;

function createFinanceChart(period) {

    if (!chartCanvas || typeof Chart === "undefined") {
        return;
    }

    let labels;
    let income;
    let expenses;

    try {

        labels = JSON.parse(
            chartCanvas.dataset.labels || "[]"
        );

        income = JSON.parse(
            chartCanvas.dataset.income || "[]"
        );

        expenses = JSON.parse(
            chartCanvas.dataset.expenses || "[]"
        );

    } catch (error) {

        console.error("Could not load chart data:", error);

        return;

    }

    // Keep the latest six or twelve months.
    const numberOfMonths = period === "12" ? 12 : 6;

    labels = labels.slice(-numberOfMonths);
    income = income.slice(-numberOfMonths);
    expenses = expenses.slice(-numberOfMonths);

    if (financeChart) {
        financeChart.destroy();
    }

    financeChart = new Chart(chartCanvas, {

        type: "line",

        data: {

            labels: labels,

            datasets: [

                {
                    label: "Income",
                    data: income,
                    borderColor: "#3478f6",
                    backgroundColor: "rgba(52, 120, 246, 0.10)",
                    borderWidth: 2.5,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    pointBackgroundColor: "#3478f6",
                    fill: true,
                    tension: 0.4
                },

                {
                    label: "Expenses",
                    data: expenses,
                    borderColor: "#62d4b0",
                    backgroundColor: "rgba(98, 212, 176, 0.05)",
                    borderWidth: 2.5,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    pointBackgroundColor: "#62d4b0",
                    fill: false,
                    tension: 0.4
                }

            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            interaction: {
                intersect: false,
                mode: "index"
            },

            plugins: {

                legend: {
                    display: false
                },

                tooltip: {

                    backgroundColor: "#101b35",
                    padding: 12,
                    cornerRadius: 8,

                    callbacks: {

                        label: function (context) {

                            return context.dataset.label + ": ₹" +
                                context.parsed.y.toLocaleString("en-IN");

                        }

                    }

                }

            },

            scales: {

                x: {

                    grid: {
                        display: false
                    },

                    border: {
                        display: false
                    },

                    ticks: {
                        color: "#8993a5",
                        font: {
                            family: "Inter",
                            size: 10
                        }
                    }

                },

                y: {

                    beginAtZero: true,

                    border: {
                        display: false
                    },

                    grid: {
                        color: "#edf0f6"
                    },

                    ticks: {

                        color: "#8993a5",

                        font: {
                            family: "Inter",
                            size: 10
                        },

                        callback: function (value) {

                            if (value >= 1000) {
                                return "₹" + (value / 1000) + "k";
                            }

                            return "₹" + value;

                        }

                    }

                }

            }

        }

    });

}


    if (chartCanvas) {

        createFinanceChart("6");

        if (chartPeriod) {

            chartPeriod.addEventListener("change", function () {
                createFinanceChart(chartPeriod.value);
            });

        }

    }

});