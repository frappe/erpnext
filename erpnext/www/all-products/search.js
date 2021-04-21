console.log("search.js loaded");

const search_box = document.getElementById("search-box");
const results = document.getElementById("results");

function populateResults(data) {
    html = ""
    for (let res of data.message) {
        html += `<li>${res}</li>`
    }
    console.log(html);
    results.innerHTML = html;
}

search_box.addEventListener("input", (e) => {
    frappe.call({
        method: "erpnext.templates.pages.product_search.search", 
        args: {
            query: e.target.value 
        },
        callback: (data) => {
            populateResults(data);
        }
    })
});