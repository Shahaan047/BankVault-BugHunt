document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("transactionSearch");
    const typeFilter = document.getElementById("typeFilter");
    const categoryFilter = document.getElementById("categoryFilter");
    const resetButton = document.getElementById("resetFilters");

    const transactionRows = Array.from(
        document.querySelectorAll(".transaction-row")
    );

    const noResultsRow = document.getElementById("noFilterResults");
    const transactionCount = document.querySelector(".transaction-count");

    function filterTransactions() {

        const searchText = searchInput.value.trim().toLowerCase();
        const selectedType = typeFilter.value;
        const selectedCategory = categoryFilter.value;

        let visibleCount = 0;

        transactionRows.forEach(function (row) {

            const name = row.dataset.name || "";
            const category = row.dataset.category || "";
            const type = row.dataset.type || "";

            const matchesSearch =
                name.includes(searchText) ||
                category.includes(searchText);

            const matchesType =
                selectedType === "all" ||
                type === selectedType;

            const matchesCategory =
                selectedCategory === "all" ||
                category === selectedCategory;

            const isVisible =
                matchesSearch &&
                matchesType &&
                matchesCategory;

            row.style.display = isVisible ? "" : "none";

            if (isVisible) {
                visibleCount++;
            }

        });

        noResultsRow.style.display =
            visibleCount === 0 ? "" : "none";

        transactionCount.textContent =
            visibleCount + (visibleCount === 1 ? " Record" : " Records");
    }

    searchInput.addEventListener("input", filterTransactions);

    typeFilter.addEventListener("change", filterTransactions);

    categoryFilter.addEventListener("change", filterTransactions);

    resetButton.addEventListener("click", function () {

        searchInput.value = "";
        typeFilter.value = "all";
        categoryFilter.value = "all";

        filterTransactions();
    });

    filterTransactions();

});