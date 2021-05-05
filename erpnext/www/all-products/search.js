let loading = false;

const searchBox = document.getElementById("search-box");
const results = document.getElementById("results");
const categoryList = document.getElementById("category-suggestions");
const showBrandLine = document.getElementById("show-brand-line");

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

