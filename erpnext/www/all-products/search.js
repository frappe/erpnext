let loading = false;

const MAX_RECENT_SEARCHES = 4;

const searchBox = document.getElementById("search-box");
const searchButton = document.getElementById("search-button");
const results = document.getElementById("results");
const categoryList = document.getElementById("category-suggestions");
const showBrandLine = document.getElementById("show-brand-line");
const recentSearchArea = document.getElementById("recent-search-chips");

function getRecentSearches() {
    return JSON.parse(localStorage.getItem("recent_searches") || "[]");
}

function attachEventListenersToChips() {
    const chips = document.getElementsByClassName("recent-chip");

    for (let chip of chips) {
        chip.addEventListener("click", () => {
            searchBox.value = chip.innerText;

            // Start search with `recent query`
            const event = new Event("input");
            searchBox.dispatchEvent(event);
            searchBox.focus();
        });
    }
}

function populateRecentSearches() {
    let recents = getRecentSearches();

    if (!recents.length) {
        return;
    }

    html = "Recent Searches: ";
    for (let query of recents) {
        html += `<button class="btn btn-secondary btn-sm recent-chip mr-1">${query}</button>`;
    }

    recentSearchArea.innerHTML = html;
    attachEventListenersToChips();
}

function populateResults(data) {
    html = ""
    for (let res of data.message) {
        html += `<li class="list-group-item list-group-item-action">
        <img class="item-thumb" src="${res.thumbnail || 'img/placeholder.png'}" />
        <a href="/${res.route}">${res.web_item_name} <span class="brand-line">${showBrandLine && res.brand ? "by " + res.brand : ""}</span></a>
        </li>`
    }
    results.innerHTML = html;
}

function populateCategoriesList(data) {
    if (data.length === 0) {
        categoryList.innerHTML = 'Type something...';
        return;
    }

    html = ""
    for (let category of data.message) {
        html += `<li>${category}</li>`
    }

    categoryList.innerHTML = html;
}

function updateLoadingState() {
    if (loading) {
        results.innerHTML = `<div class="spinner-border"><span class="sr-only">loading...<span></div>`;
    }
}

searchBox.addEventListener("input", (e) => {
    loading = true;
    updateLoadingState();
    frappe.call({
        method: "erpnext.templates.pages.product_search.search", 
        args: {
            query: e.target.value 
        },
        callback: (data) => {
            populateResults(data);
            loading = false;
        }
    });

    // If there is a suggestion list node
    if (categoryList) {
        frappe.call({
            method: "erpnext.templates.pages.product_search.get_category_suggestions",
            args: {
                query: e.target.value
            },
            callback: (data) => {
                populateCategoriesList(data);
            }
        });
    }
});

searchButton.addEventListener("click", (e) => {
    let query = searchBox.value;
    if (!query) {
        return;
    }

    let recents = getRecentSearches();

    if (recents.length >= MAX_RECENT_SEARCHES) {
        // Remove the `First` query
        recents.splice(0, 1);
    }

    if (recents.indexOf(query) >= 0) {
        return;
    }

    recents.push(query);

    localStorage.setItem("recent_searches", JSON.stringify(recents));

    // Refresh recent searches
    populateRecentSearches();
});

populateRecentSearches();