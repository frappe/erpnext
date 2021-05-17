erpnext.ProductView =  class {
	/* Options:
		- View Type
		- Products Section Wrapper,
		- Item Group: If its an Item Group page
	*/
	constructor(options) {
		Object.assign(this, options);
		this.preference = "List View";

		this.products_section.empty();
		this.prepare_view_toggler();
		this.get_item_filter_data();
	}

	prepare_view_toggler() {
		if(!$("#list").length || !$("#image-view").length) {
			this.render_view_toggler();
			this.bind_view_toggler_actions();
			this.set_view_state();
		}
	}

	get_item_filter_data() {
		// Get and render all Items related components
		let me = this;
		let args = this.get_query_filters();

		$('#list').prop('disabled', true);
		$('#image-view').prop('disabled', true);
		frappe.call({
			method: 'erpnext.www.all-products.index.get_product_filter_data',
			args: args,
			callback: function(result) {
				if (!result.exc && result) {
					me.render_filters(result.message[1]);

					if (me.item_group) {
						me.render_item_sub_categories(result.message[3]);
					}
					// Render views
					me.render_list_view(result.message[0], result.message[2]);
					me.render_grid_view(result.message[0], result.message[2]);
					me.products = result.message[0];

					// Bottom paging
					me.add_paging_section(result.message[2]);
				} else {
					me.render_no_products_section();
				}

				$('#list').prop('disabled', false);
				$('#image-view').prop('disabled', false);
			}
		});
	}

	render_filters(filter_data) {
		this.get_discount_filter_html(filter_data.discount_filters);
	}

	render_grid_view(items, settings) {
		// loop over data and add grid html to it
		let me = this;
		this.prepare_product_area_wrapper("grid");

		frappe.require('assets/js/e-commerce.min.js', function() {
			new erpnext.ProductGrid({
				items: items,
				products_section: $("#products-grid-area"),
				settings: settings,
				preference: me.preference
			});
		});
	}

	render_list_view(items, settings) {
		let me = this;
		this.prepare_product_area_wrapper("list");

		frappe.require('assets/js/e-commerce.min.js', function() {
			new erpnext.ProductList({
				items: items,
				products_section: $("#products-list-area"),
				settings: settings,
				preference: me.preference
			});
		});
	}

	prepare_product_area_wrapper(view) {
		let left_margin = view == "list" ? "ml-2" : "";
		let top_margin = view == "list" ? "mt-8" : "mt-4";
		return this.products_section.append(`
			<br>
			<div id="products-${view}-area" class="row products-list ${ top_margin } ${ left_margin }"></div>
		`);
	}

	get_query_filters() {
		const filters = frappe.utils.get_query_params();
		let {field_filters, attribute_filters} = filters;

		field_filters = field_filters ? JSON.parse(field_filters) : {};
		attribute_filters = attribute_filters ? JSON.parse(attribute_filters) : {};

		return {
			field_filters: field_filters,
			attribute_filters: attribute_filters,
			item_group: this.item_group,
			start: filters.start || null
		}
	}

	add_paging_section(settings) {
		$(".product-paging-area").remove();

		if(this.products) {
			let paging_html = `
				<div class="row product-paging-area mt-5">
					<div class="col-3">
					</div>
					<div class="col-9 text-right">
			`;
			let query_params = frappe.utils.get_query_params();
			let start = query_params.start ? cint(JSON.parse(query_params.start)) : 0;
			let page_length = settings.products_per_page || 0;

			if(start > 0) {
				paging_html += `
					<button class="btn btn-default btn-prev" data-start="${ start - page_length }" style="float: left">
						${ __("Prev") }
					</button>`;
			}
			if(this.products.length > page_length || this.products.length == page_length) {
				paging_html += `
					<button class="btn btn-default btn-next" data-start="${ start + page_length }">
						${ __("Next") }
					</button>
				`;
			}
			paging_html += `</div></div>`;

			$(".page_content").append(paging_html);
			this.bind_paging_action();
		}
	}

	render_view_toggler() {
		["btn-list-view", "btn-grid-view"].forEach(view => {
			let icon = view === "btn-list-view" ? "list" : "image-view";
			this.products_section.append(`
			<div class="form-group mb-0" id="toggle-view">
				<button id="${ icon }" class="btn ${ view } mr-2">
					<span>
						<svg class="icon icon-md">
							<use href="#icon-${ icon }"></use>
						</svg>
					</span>
				</button>
			</div>`);
		});
	}

	bind_view_toggler_actions() {
		$("#list").click(function() {
			let $btn = $(this);
			$btn.removeClass('btn-primary');
			$btn.addClass('btn-primary');
			$(".btn-grid-view").removeClass('btn-primary');

			$("#products-grid-area").addClass("hidden");
			$("#products-list-area").removeClass("hidden");
		})

		$("#image-view").click(function() {
			let $btn = $(this);
			$btn.removeClass('btn-primary');
			$btn.addClass('btn-primary');
			$(".btn-list-view").removeClass('btn-primary');

			$("#products-list-area").addClass("hidden");
			$("#products-grid-area").removeClass("hidden");
		});
	}

	set_view_state() {
		if (this.preference === "List View") {
			$("#list").addClass('btn-primary');
			$("#image-view").removeClass('btn-primary');
		} else {
			$("#image-view").addClass('btn-primary');
			$("#list").removeClass('btn-primary');
		}
	}

	bind_paging_action() {
		$('.btn-prev, .btn-next').click((e) => {
			const $btn = $(e.target);
			$btn.prop('disabled', true);
			const start = $btn.data('start');
			let query_params = frappe.utils.get_query_params();
			query_params.start = start;
			let path = window.location.pathname + '?' + frappe.utils.get_url_from_dict(query_params);
			window.location.href = path;
		});
	}

	get_discount_filter_html(filter_data) {
		$("#discount-filters").remove();
		if (filter_data) {
			$("#product-filters").append(`
				<div id="discount-filters" class="mb-4 filter-block pb-5">
					<div class="filter-label mb-3">${ __("Discounts") }</div>
				</div>
			`);

			let html = `<div class="filter-options">`;
			filter_data.forEach(filter => {
				html += `
					<div class="checkbox">
						<label data-value="${ filter[0] }">
							<input type="radio" class="product-filter discount-filter"
								name="discount" id="${ filter[0] }"
								data-filter-name="discount" data-filter-value="${ filter[0] }"
							>
								<span class="label-area" for="${ filter[0] }">
									${ filter[1] }
								</span>
						</label>
					</div>
				`;
			});
			html += `</div>`;

			$("#discount-filters").append(html);
		}
	}

	render_no_products_section() {
		$("#products-area").append(`
			<div class="d-flex justify-content-center p-3 text-muted">
				${ __('No products found') }
			</div>
		`);
	}

	render_item_sub_categories(categories) {
		if(categories) {
			let sub_group_html = `
				<div class="sub-category-container">
					<div class="heading"> ${ __('Sub Categories') } </div>
				</div>
				<div class="sub-category-container scroll-categories">
			`;

			categories.forEach(category => {
				sub_group_html += `
					<a href="${ category.route || '#' }" style="text-decoration: none;">
						<div class="category-pill">
							${ category.name }
						</div>
					</a>
				`;
			})
			sub_group_html += `</div>`;

			$("#product-listing").prepend(sub_group_html);
		}
	}
}