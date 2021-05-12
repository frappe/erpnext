erpnext.ProductView =  class {
	/* Options: View Type */
	constructor(options) {
		Object.assign(this, options);
		this.render_view_toggler();
		this.get_item_filter_data();
		this.render_list_view();
		this.render_grid_view();
	}

	render_view_toggler() {
		["btn-list-view", "btn-grid-view"].forEach(view => {
			let icon = view === "btn-list-view" ? "list" : "image-view";
			this.products_section.append(`
			<div class="form-group mb-0" id="toggle-view">
				<button id="${icon}" class="btn ${view} mr-2">
					<span>
						<svg class="icon icon-md">
							<use href="#icon-${icon}"></use>
						</svg>
					</span>
				</button>
			</div>`);
		});

		$("#list").click(function() {
			let $btn = $(this);
			$btn.removeClass('btn-primary');
			$btn.addClass('btn-primary');
			$(".btn-grid-view").removeClass('btn-primary');
		})

		$("#image-view").click(function() {
			let $btn = $(this);
			$btn.removeClass('btn-primary');
			$btn.addClass('btn-primary');
			$(".btn-list-view").removeClass('btn-primary');
		});

		this.products_area = this.products_section.append(`
			<br><br>
			<div id="products-area" class="row products-list mt-4"></div>
		`);
	}

	get_item_filter_data() {
		// Get Items and Discount Filters to render
		let me = this;
		const filters = frappe.utils.get_query_params();
		let {field_filters, attribute_filters} = filters;

		field_filters = field_filters ? JSON.parse(field_filters) : {};
		attribute_filters = attribute_filters ? JSON.parse(attribute_filters) : {};

		frappe.call({
			method: 'erpnext.www.all-products.index.get_product_filter_data',
			args: {
				field_filters: field_filters,
				attribute_filters: attribute_filters,
				item_group: me.item_group
			},
			callback: function(result) {
				if (!result.exc) {
					me.render_filters(result.message[1]);

					// Append pre-rendered products
					// TODO: get products as is and style via js
					me.products = result.message;
					$("#products-area").append(result.message[0]);

				} else {
					$("#products-area").append(`
						<div class="d-flex justify-content-center p-3 text-muted">
							${__('No products found')}
						</div>`);

				}
			}
		});
	}

	render_filters(filter_data) {
		this.get_discount_filter_html(filter_data.discount_filters);
	}

	get_discount_filter_html(filter_data) {
		if (filter_data) {
			$("#product-filters").append(`
				<div id="discount-filters" class="mb-4 filter-block pb-5">
					<div class="filter-label mb-3">${__("Discounts")}</div>
				</div>
			`);

			let html = `<div class="filter-options">`;
			filter_data.forEach(filter => {
				html += `
					<div class="checkbox">
						<label data-value="${filter[0]}">
							<input type="radio" class="product-filter discount-filter"
								name="discount" id="${filter[0]}"
								data-filter-name="discount" data-filter-value="${filter[0]}"
							>
								<span class="label-area" for="${filter[0]}">
									${filter[1]}
								</span>
						</label>
					</div>
				`;
			});
			html += `</div>`;

			$("#discount-filters").append(html);
		}
	}

	render_list_view() {
		// loop over data and add list html to it
	}

	render_grid_view() {
		// loop over data and add grid html to it
	}

}