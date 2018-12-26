$(() => {
    let filters = {}
    $('.product-filter').on('change', (e) => {
        const $checkbox = $(e.target);
        const is_checked = $checkbox.is(':checked');
        const { attribute, attributeValue } = $checkbox.data();

        if (is_checked) {
            filters[attribute] = filters[attribute] || [];
            filters[attribute].push(attributeValue);
        } else {
            filters[attribute] = filters[attribute] || [];
            filters[attribute] = filters[attribute].filter(v => v !== attributeValue);
        }

        const query_string = get_query_string();
        window.history.pushState('filters', '', '/products?' + query_string);

        get_items_with_filters()
            .then(html => {
                $('.products-list').html(html)
            })
    });

    function get_items_with_filters() {
        return new Promise(resolve => {
            frappe.call('erpnext.templates.pages.products.get_products_html_for_website', {
                attribute_data: filters
            }).then(r => resolve(r.message))
        })
    }

    function get_query_string() {
        const url = new URLSearchParams();
        for (let key in filters) {
            const value = filters[key].join(',');
            if (value) {
                url.append(key, value)
            }
        }
        return url.toString();
    }
});