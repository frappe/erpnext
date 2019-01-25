$(() => {
	class ProductListing {
		constructor() {
			this.bind_filters();
			this.bind_search();
			this.restore_filters_state();
		}

		bind_filters() {
			this.field_filters = {};
			this.attribute_filters = {};

			$('.product-filter').on('change', frappe.utils.debounce((e) => {
				const $checkbox = $(e.target);
				const is_checked = $checkbox.is(':checked');

				if ($checkbox.is('.attribute-filter')) {
					const {
						attributeName: attribute_name,
						attributeValue: attribute_value
					} = $checkbox.data();

					if (is_checked) {
						this.attribute_filters[attribute_name] = this.attribute_filters[attribute_name] || [];
						this.attribute_filters[attribute_name].push(attribute_value);
					} else {
						this.attribute_filters[attribute_name] = this.attribute_filters[attribute_name] || [];
						this.attribute_filters[attribute_name] = this.attribute_filters[attribute_name].filter(v => v !== attribute_value);
					}

					if (this.attribute_filters[attribute_name].length === 0) {
						delete this.attribute_filters[attribute_name];
					}
				} else if ($checkbox.is('.field-filter')) {
					const {
						filterName: filter_name,
						filterValue: filter_value
					} = $checkbox.data();

					if (is_checked) {
						this.field_filters[filter_name] = this.field_filters[filter_name] || [];
						this.field_filters[filter_name].push(filter_value);
					} else {
						this.field_filters[filter_name] = this.field_filters[filter_name] || [];
						this.field_filters[filter_name] = this.field_filters[filter_name].filter(v => v !== filter_value);
					}

					if (this.field_filters[filter_name].length === 0) {
						delete this.field_filters[filter_name];
					}
				}

				const query_string = get_query_string({
					field_filters: JSON.stringify(if_key_exists(this.field_filters)),
					attribute_filters: JSON.stringify(if_key_exists(this.attribute_filters)),
				})
				window.history.pushState('filters', '', '/products?' + query_string);

				$('.page_content input').prop('disabled', true);
				this.get_items_with_filters()
					.then(html => {
						$('.products-list').html(html)
					})
					.then(data => {
						$('.page_content input').prop('disabled', false);
						return data;
					})
					.catch(e => {
						console.log(e);
						$('.page_content input').prop('disabled', false);
					});
			}, 1000));
		}

		make_filters() {

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

		restore_filters_state() {
			const filters = frappe.utils.get_query_params();
			let {field_filters, attribute_filters} = filters;

			if (field_filters) {
				field_filters = JSON.parse(field_filters);
				for (let fieldname in field_filters) {
					const values = field_filters[fieldname];
					const selector = values.map(value => {
						return `input[data-filter-name="${fieldname}"][data-filter-value="${value}"]`
					}).join(',');
					$(selector).prop('checked', true);
				}
				this.field_filters = field_filters;
			}
			if (attribute_filters) {
				attribute_filters = JSON.parse(attribute_filters);
				for (let attribute in attribute_filters) {
					const values = attribute_filters[attribute];
					const selector = values.map(value => {
						return `input[data-attribute-name="${attribute}"][data-attribute-value="${value}"]`
					}).join(',');
					$(selector).prop('checked', true);
				}
				this.attribute_filters = attribute_filters;
			}
		}

		get_items_with_filters() {
			const { attribute_filters, field_filters } = this;
			const args = {
				field_filters: if_key_exists(field_filters),
				attribute_filters: if_key_exists(attribute_filters)
			};

			return new Promise((resolve, reject) => {
				frappe.call('erpnext.www.products.index.get_products_html_for_website', args)
					.then(r => {
						if (r.exc) reject(r.exc);
						else resolve(r.message);
					})
					.fail(reject);
			});
		}
	}

	new ProductListing();

	function get_query_string(object) {
		const url = new URLSearchParams();
		for (let key in object) {
			const value = object[key];
			if (value) {
				url.append(key, value)
			}
		}
		return url.toString();
	}

	function if_key_exists(obj) {
		let exists = false;
		for (let key in obj) {
			if (obj.hasOwnProperty(key) && obj[key]) {
				exists = true;
				break;
			}
		}
		return exists ? obj : undefined;
	}
});
