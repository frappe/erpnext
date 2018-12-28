$(() => {
    class ProductListing {
        constructor() {
            this.bind_filters();
            this.bind_search();
        }

        bind_filters() {
            this.filters = {}
            $('.product-filter').on('change', (e) => {
                const $checkbox = $(e.target);
                const is_checked = $checkbox.is(':checked');
                const { attribute, attributeValue } = $checkbox.data();

                if (is_checked) {
                    this.filters[attribute] = this.filters[attribute] || [];
                    this.filters[attribute].push(attributeValue);
                } else {
                    this.filters[attribute] = this.filters[attribute] || [];
                    this.filters[attribute] = this.filters[attribute].filter(v => v !== attributeValue);
                }

                if (this.filters[attribute].length === 0) {
                    delete this.filters[attribute];
                }

                const query_string = this.get_query_string();
                window.history.pushState('filters', '', '/products?' + query_string);

                this.get_items_with_filters()
                    .then(html => {
                        $('.products-list').html(html)
                    })
            });
        }

        bind_search() {
            $('input[type=search]').on('keydown', (e) => {
                if (e.keyCode === 13) {
                    // Enter
                    const value = e.target.value;
                    if (value) {
                        window.location.search = 'search=' + e.target.value
                    } else {
                        window.location.search = ''
                    }
                }
            })
        }

        get_items_with_filters() {
            const filters = this.filters;
            return new Promise(resolve => {
                frappe.call('erpnext.www.products.index.get_products_html_for_website', {
                    attribute_data: Object.keys(filters).length > 0 ? filters : null
                }).then(r => resolve(r.message))
            })
        }

        get_query_string() {
            const filters = this.filters;
            const url = new URLSearchParams();
            for (let key in filters) {
                const value = filters[key].join(',');
                if (value) {
                    url.append(key, value)
                }
            }
            return url.toString();
        }
    }

    new ProductListing();
});
