console.log("search.js reloaded");

const search_box = document.getElementById("search-box");
const results = document.getElementById("results");

function populateResults(data) {
    console.log(data);
    html = ""
    for (let res of data.message) {
        html += `<li>
        <img class="item-thumb" src="${res.thumbnail || ''}" />
        <a href="/${res.route}">${res.web_item_name}</a>
        </li>`
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