console.log("search.js loaded");

const searchBox = document.getElementById("search-box");
const results = document.getElementById("results");
const categoryList = document.getElementById("category-suggestions");

function populateResults(data) {
    html = ""
    for (let res of data.message) {
        html += `<li>
        <img class="item-thumb" src="${res.thumbnail || ''}" />
        <a href="/${res.route}">${res.web_item_name}</a>
        </li>`
    }
    results.innerHTML = html;
}

function populateCategoriesList(data) {
    if (data.length === 0) {
        categoryList.innerText = "No matches";
        return;
    }

    html = ""
    for (let category of data.message) {
        html += `<li>${category}</li>`
    }

    categoryList.innerHTML = html;
}

searchBox.addEventListener("input", (e) => {
    frappe.call({
        method: "erpnext.templates.pages.product_search.search", 
        args: {
            query: e.target.value 
        },
        callback: (data) => {
            populateResults(data);
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

