/* globals Hub, HubList */

frappe.provide('erpnext.hub');

frappe.pages['hub'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Hub',
		single_col: false
	});

	wrapper.hub_page = new erpnext.hub.Hub({ page });
};

frappe.pages['hub'].on_page_show = function(wrapper) {
	const hub_page = wrapper.hub_page;
	const [hub, type, id] = frappe.get_route();

	if (!(hub || type || id)) {
		hub_page.go_to_home_page();
		return;
	}

	if (type === "Products") {
		hub_page.go_to_item_page(id);
	} else if (type === "Company") {
		hub_page.go_to_company_page(id);
	}
}

erpnext.hub.Hub = class Hub {
	constructor({ page }) {
		this.page = page;
		frappe.require('/assets/erpnext/css/hub.css', () => {
			this.setup();
		});
	}

	setup() {
		this.setup_header();
		this.company_cache = {};
		this.item_cache = {};
		this.filters = {};
		this.order_by = '';

		this.$hub_main_section =
			$(`<div class='hub-main-section'>`).appendTo(this.page.body);
		this.bind_events();
		this.refresh();
	}

	refresh() {
		this.$hub_main_section.empty();
		this.page.page_form.hide();

		const $layout_main = this.page.wrapper.find('.layout-main');
		const $page_head = this.page.wrapper.find('.page-head');

		frappe.model.with_doc('Hub Settings', 'Hub Settings', () => {
			this.hub_settings = frappe.get_doc('Hub Settings');

			if(this.hub_settings.enabled == 0) {
				let $empty_state = this.page.get_empty_state(
					__("Register for Hub"),
					__(`Let other ERPNext users discover your products
						and automate workflow with Supplier from within ERPNext.`),
					__("Register")
				);

				$page_head.hide();
				$layout_main
					.find('.layout-side-section, .layout-main-section-wrapper')
					.hide();
				$layout_main.append($empty_state);

				$empty_state.find('.btn-primary').on('click', () => {
					this.register_for_hub();
				});
			} else {
				$page_head.show();
				$layout_main.find('.page-card-container').remove();
				$layout_main.find('.layout-side-section, .layout-main-section-wrapper').show();
				this.setup_live_state();
			}
		});
	}

	register_for_hub() {
		if (frappe.session.user.includes('Administrator')) {
			frappe.throw(__('Please login as another user.'))
		}
		frappe.verify_password(() => {
			frappe.call({
				method: 'erpnext.hub_node.enable_hub',
				callback: (r) => {
					if(r.message.enabled == 1) {
						Object.assign(this.hub_settings, r.message);
						this.refresh();
						this.prompt_for_item_sync();
					}
				}
			});
		});
	}

	prompt_for_item_sync() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Data Migration Run',
				filters: {
					'data_migration_plan': 'Hub Sync'
				},
				limit_page_length: 1
			},
			callback: function(r) {
				if (!r) {
					frappe.confirm(__('Do you want to publish your Items to Hub ?'), () => {
						this.sync_items_to_hub();
					});
				}
			}
		})
	}

	setup_header() {
		this.page.page_title = this.page.wrapper.find('.page-title');
		this.tag_line = $(`
			<div class='tag-line-container'>
				<span class='tag-line text-muted small'>
					${__('Product listing and discovery for ERPNext users')}
				</span>
			</div>`)
			.appendTo(this.page.page_title);

		this.bind_title();
	}

	setup_live_state() {
		if(!this.$search) {
			this.setup_filters();
		}
		this.page.page_form.show();
		this.setup_menu();
		this.setup_sidebar();
		this.render_body();
		this.setup_lists();
	}

	setup_filters() {

		// frappe.call({
		// 	method: 'erpnext.hub_node.get_categories'
		// }).then((r) => {
		// 	if (r.message) {
		// 		const categories = r.message;
		// 		console.log("categories", categories);
		// 		categories
		// 			.map(c => c.hub_category_name)
		// 			.map(c => this.sidebar.add_item({
		// 				label: c,
		// 				on_click: () => {
		// 					this.home_item_list &&
		// 					this.home_item_list.refresh({
		// 						text: '',
		// 						start: 0,
		// 						limit: 20,
		// 						category: c && c !== 'All Categories' ? c : undefined
		// 					});
		// 				}
		// 			}, __('Hub Category')));


		// 	}
		// });

		// this.category_select = this.page.add_select(__('Category'),
		// 	[
		// 		{label: __('Sort by Price ...'), value: '' },
		// 		{label: __('High to Low'), value: 'price desc' },
		// 		{label: __('Low to High'), value: 'price' },
		// 	]
		// );

		this.price_sort_select = this.page.add_select(__('Sort by Price'),
			[
				{label: __('Sort by Price ...'), value: '' },
				{label: __('High to Low'), value: 'price desc' },
				{label: __('Low to High'), value: 'price' },
			]
		);

		this.criteria_select = this.page.add_select(__('Sort by Criteria'),
			[
				{label: __('Most Popular'), value: 'request_count' },
				{label: __('Newest'), value: 'creation' },
			]
		);

		this.price_sort_select.on('change', () => {
			this.refresh_item_only_page();
		});

		this.criteria_select.on('change', () => {
			this.refresh_item_only_page();
		});

		this.setup_hub_category_filter();
		this.setup_search();
	}

	bind_events() {
		const me = this;
		this.$hub_main_section
			.on('click', '.company-link a', function(e) {
				e.preventDefault();
				const company_name = $(this).attr('data-company-name');
				frappe.set_route('hub', 'Company', company_name);
			})
			.on('click', '.breadcrumb li', function(e) {
				e.preventDefault();
				const $li = $(this);
				if ($li.attr('data-route') === 'Home') {
					me.go_to_home_page();
				}
			});
	}

	update_filters() {
		let price_sort = $(this.price_sort_select).val() || '';
		let criteria = $(this.criteria_select).val() || '';

		let order_by_params = [];
		let query_string = '';
		if(criteria) {
			order_by_params.push(criteria);
			// query_string += 'sort_by=' + criteria
		}
		if(price_sort) order_by_params.push(price_sort);
		this.order_by = order_by_params.join(",");
		// return query_string;
	}

	reset_filters() {
		this.order_by = '';
		$(this.category_select).val('');
		$(this.price_sort_select).val('');
		$(this.criteria_select).val('Most Popular');
	}

	refresh_item_only_page() {
		this.reset_search();
		this.update_filters();
		this.go_to_items_only_page(
			['hub', 'Products'],
			'', 'product-list'
		);
	}

	bind_title() {
		this.page.page_title.find('.title-text').on('click', () => {
			this.go_to_home_page();
		});
	}

	render_body() {
		this.$home_page = $(`
			<div class = 'hub-home-page'>
				<div class='banner'></div>
				<div class='listing-body row'>
					<div class='main-list-section'></div>
				</div>
			</div>
		`).appendTo(this.$hub_main_section);

		this.$banner = this.$hub_main_section.find('.banner');
		this.$listing_body = this.$hub_main_section.find('.listing-body');
		this.$main_list_section = this.$hub_main_section.find('.main-list-section');
		this.$side_list_section = this.$hub_main_section.find('.side-list-section');
	}

	setup_lists() {
		this.home_item_list = new erpnext.hub.HubList({
			parent: this.$main_list_section,
			title: 'New',
			page_length: 20,
			list_css_class: 'home-product-list',
			method: 'erpnext.hub_node.get_items',
			// order_by: 'request_count',
			filters: {text: '', country: this.country}, // filters at the time of creation
			on_item_click: (item_code) => {
				frappe.set_route('hub', 'Products', item_code);
			}
		});

		this.home_item_list.setup();
	}

	setup_hub_category_filter() {
		const me = this;

		this.hub_category_field = this.page.add_field({
			fieldtype: 'Autocomplete',
			label: 'Hub Category',
			change() {
				let value = this.get_value();
				let title = value;
				if (value === 'All Categories') {
					// show all items
					value = null;
				}

				me.home_item_list.title = title;
				me.home_item_list.refresh({
					text: '',
					start: 0,
					limit: 20,
					category: value
				});
			}
		});

		frappe.call('erpnext.hub_node.get_categories')
			.then((r) => {
				if (r.message) {
					const categories = r.message;

					this.hub_category_field.set_data(
						categories.map(c => c.hub_category_name)
					);
				}
			});
	}

	setup_search() {
		this.$search = this.page.add_data(__('Search'));
		this.$search.on('keypress', (e) => {
			if(e.which === 13) {
				var search_term = ($(this.$search).val() || '').toLowerCase();
				this.go_to_items_only_page(
					['hub', 'search', search_term],
					'Search results for \''  + search_term + '\'',
					'search-product-list',
					{text: search_term}
				);
			}
		});
	}

	go_to_items_only_page(route, title, class_name, filters = {text: ''}, by_item_codes=0) {
		frappe.set_route(route);
		this.$hub_main_section.empty();
		this.filtered_item_list = new erpnext.hub.HubList({
			parent: this.$hub_main_section,
			title: title,
			page_length: 20,
			list_css_class: class_name,
			method: 'erpnext.hub_node.get_items',
			order_by: this.order_by,
			filters: filters,
			by_item_codes: by_item_codes
		});
		this.filtered_item_list.on_item_click = (item_code) => {
			frappe.set_route('hub', 'Products', item_code);
		}
		this.filtered_item_list.setup();
	}

	go_to_item_page(item_code) {
		if(this.item_cache) {
			let item = this.item_cache[item_code];
			if(item) {
				this.render_item_page(item);
				return;
			}
		} else {
			this.item_cache = {};
		}
		frappe.call({
			args:{
				hub_sync_id: item_code
			},
			method: "erpnext.hub_node.get_item_details",
			callback: (r) => {
				if (!r || !r.message) return;
				let item = r.message;
				this.item_cache[item_code] = item;
				this.render_item_page(item);
			}
		});
	}

	render_item_page(item) {
		this.$hub_main_section.empty();


		let $item_page =
			$(this.get_item_page(item))
				.appendTo(this.$hub_main_section);

		let $company_items = $item_page.find('.company-items');

		let company_item_list = new erpnext.hub.HubList({
			parent: $company_items,
			title: 'More by ' + item.company_name,
			page_length: 5,
			list_css_class: 'company-item-list',
			method: 'erpnext.hub_node.get_items',
			// order_by: 'request_count',
			filters: {text: '', company_name: item.company_name, country: this.country},
			paginated: 0,
			img_size: 150
		});

		company_item_list.on_item_click = (item_code) => {
			frappe.set_route('hub', 'Products', item_code);
		}
		company_item_list.setup();

		$item_page.find('.rfq-btn')
			.click((e) => {
				const $btn = $(e.target);

				this.show_rfq_modal(item)
					.then(values => {
						item.item_code = values.item_code;
						delete values.item_code;

						const supplier = values;
						return [item, supplier];
					})
					.then(([item, supplier]) => {
						return this.make_rfq(item, supplier, $btn);
					})
					.then(r => {
						console.log(r);
						if (r.message && r.message.rfq) {
							$btn.addClass('disabled').html(`<span><i class='fa fa-check'></i> ${__('Quote Requested')}</span>`);
						} else {
							throw r;
						}
					})
					.catch((e) => {
						console.log(e); //eslint-disable-line
					});
			});
	}

	show_rfq_modal(item) {
		return new Promise(res => {
			let fields = [
				{ label: __('Item Code'), fieldtype: 'Data', fieldname: 'item_code', default: item.item_code },
				{ fieldtype: 'Column Break' },
				{ label: __('Item Group'), fieldtype: 'Link', fieldname: 'item_group', default: item.item_group },
				{ label: __('Supplier Details'), fieldtype: 'Section Break' },
				{ label: __('Supplier Name'), fieldtype: 'Data', fieldname: 'supplier_name', default: item.company_name },
				{ label: __('Supplier Email'), fieldtype: 'Data', fieldname: 'supplier_email', default: item.seller },
				{ fieldtype: 'Column Break' },
				{ label: __('Supplier Type'), fieldname: 'supplier_type',
					fieldtype: 'Link', options: 'Supplier Type' }
			];
			fields = fields.map(f => { f.reqd = 1; return f; });

			const d = new frappe.ui.Dialog({
				title: __('Request for Quotation'),
				fields: fields,
				primary_action_label: __('Send'),
				primary_action: (values) => {
					res(values);
					d.hide();
				}
			});

			d.show();
		});
	}

	get_company_details(company_id) {
		this.company_cache = this.company_cache || {};

		return new Promise(resolve => {
			// get from cache if exists
			let company_details = this.company_cache[company_id];
			if(company_details) {
				resolve(company_details);
				return;
			}
			frappe.call({
				method: 'erpnext.hub_node.get_company_details',
				args: {hub_sync_id: company_id}
			}).then((r) => {
				if (r.message) {
					const company_details = r.message;
					this.company_cache[company_id] = company_details;
					resolve(company_details)
				}
			});
		})
	}

	go_to_company_page(company_id) {
		this.get_company_details(company_id)
			.then(this.show_company_page.bind(this));
	}

	show_company_page(company_details) {
		this.$hub_main_section.empty();

		let $company_page =
			$(this.get_company_page(company_details))
				.appendTo(this.$hub_main_section);

		let $company_items = $company_page.find('.company-items');

		let company_item_list = new erpnext.hub.HubList({
			parent: $company_items,
			title: 'More by ' + company_details.company_name,
			page_length: 5,
			list_css_class: 'company-item-list',
			method: 'erpnext.hub_node.get_items',
			// order_by: 'request_count',
			filters: {text: '', company: company_details.company_name, country: this.country},
			paginated: 0,
			img_size: 150
		});

		company_item_list.on_item_click = (item_code) => {
			frappe.set_route('hub', 'Products', item_code);
		}
		company_item_list.setup();
	}

	get_item_page(item) {
		return `
			<div class="hub-item-page">
				<div class="item-header">
					<div class="item-page-image">
						${ this.home_item_list.get_item_image(item) }
					</div>
					<div class="title-content">
						<div class="breadcrumbs">
							${this.get_breadcrumb(item.item_name, "Products") }
						</div>
						<div class="title">
							<h2>${ item.item_name }</h2>
						</div>
						<div class="company">
							<span class="">${ item.company_name }</span>
						</div>
						<div class="category">
							<span class="text-muted">Products</span>
						</div>
						<div class="description">
							<span class="small">${ item.description ? item.description : "" }</span>
						</div>
						<div class="price">
							${ item.formatted_price ? item.formatted_price : '' }
						</div>
						<div class="actions">
							<a class="btn btn-primary rfq-btn">Request A Quote</a>
						</div>
					</div>

				</div>
				<div class="item-more-info"></div>
				<div class="company-items">

				</div>
			</div>
		`;
	}

	get_company_page(company_details) {
		return `
			<div class="hub-item-page">
				<div class="item-header">
					<div class="title-content">
						<div class="breadcrumbs">
							${this.get_breadcrumb(company_details.company_name, "Company") }
						</div>
						<div class="title">
							<h2>${ company_details.company_name }</h2>
						</div>
						<div class="company">
							<span class="">${ company_details.country }</span>
						</div>
						<div class="description">
							<span class="small">${ company_details.site_name }</span>
						</div>
					</div>

				</div>
				<div class="item-more-info"></div>
				<div class="company-items">

				</div>
			</div>
		`;
	}

	get_breadcrumb(name, type) {
		return `
			<ul class="breadcrumb">
				<li data-route="Home">
					<a href><span>Home</span></a>
				</li>
				<li data-route="List">
					<a href><span>${type}</span></a>
				</li>
				<li class="active">
					<span>${name}</span>
				</li>
			</ul>
		`;
	}

	go_to_home_page() {
		frappe.set_route('hub');
		this.reset_filters();
		this.refresh();
	}

	setup_menu() {
		if (this.menu_setup) return;

		this.page.add_menu_item(__('Hub Settings'),
			() => frappe.set_route('Form', 'Hub Settings'));
		this.page.add_menu_item(__('Refresh'), () => this.refresh());
		this.page.add_menu_item(__('Sync'), () => this.sync_items_to_hub());

		this.menu_setup = true;
	}

	sync_items_to_hub() {
		frappe.call('erpnext.hub_node.doctype.hub_settings.hub_settings.sync')
	}

	setup_sidebar() {
		var me = this;
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.page.wrapper.find('.layout-side-section'),
			css_class: 'hub-sidebar'
		});

		this.add_account_to_sidebar();
	}

	add_account_to_sidebar() {
		this.sidebar.add_item({
			label: this.hub_settings.company,
			on_click: () => frappe.set_route('Form', 'Company', this.hub_settings.company)
		}, __("Account"));

		this.sidebar.add_item({
			label: __("My Orders"),
			on_click: () => frappe.set_route('List', 'Request for Quotation')
		}, __("Account"));
	}

	get_search_term() {
		return this.$search.val();
	}

	reset_search() {
		this.$search.val('');
	}

	make_rfq(item, supplier, btn) {
		console.log(supplier);
		return new Promise((resolve, reject) => {
			frappe.call({
				method: 'erpnext.hub_node.make_rfq_and_send_opportunity',
				args: { item, supplier },
				callback: resolve,
				btn,
			}).fail(reject);
		});
	}

	go_to_seen_items() {
		this.go_to_items_only_page(
			['hub', 'Requested Products'],
			__('Requested Products'),
			'requested-product-list',
			{}, 1
		);
	}
}

erpnext.hub.HubList = class HubList {
	constructor({
		parent = null,
		title = 'Products',
		page_length = 20,
		list_css_class = '',
		method = 'erpnext.hub_node.get_items',
		filters = {text: ''},
		order_by = '',
		by_item_codes = 0,
		paginated = 1,
		on_item_click = null,
		img_size = 200
	}) {
		this.parent = parent;
		this.title = title;
		this.page_length = page_length;
		this.list_css_class = list_css_class;
		this.method = method;
		this.filters = filters;
		this.order_by = order_by;
		this.by_item_codes = by_item_codes;
		this.paginated = paginated;

		this.on_item_click = on_item_click;
		this.img_size = img_size;
	}

	// to be called on demand
	setup() {
		this.container = $(`
			<div class='item-list-container ${this.list_css_class}' data-page-length='${this.page_length}'>
				<div class='item-list-header'>
					<h3>${this.title}</h3>
				</div>
				<div class='item-list'></div>
				<div class='list-state'>
					<div class='loading'>
						<p class='text-muted text-center'>${__('Loading...')}</p>
					</div>
					<div class='done hide'>
						<p class='text-muted text-center'>${__('No more results')}</p>
					</div>
					<div class='more text-right'>
						<button class='btn btn-default btn-sm'>${__('More')}</div>
					</div>
				</div>
			</div>`)
			.appendTo(this.parent);

		this.$item_list_title = this.container.find('.item-list-header h3');
		this.$list = this.container.find('.item-list');
		this.$loading = this.container.find('.loading').hide();
		this.$more = this.container.find('.more').hide();
		this.$done = this.container.find('.done');

		this.$more.on('click', () => {
			this.next_page();
		});

		this.next_page();
	}

	refresh(filters = this.filters) {
		this.reset();
		this.set_filters(filters);
		this.next_page();
	}

	reset() {
		this.$list.empty();
	}

	set_filters(filters) {
		this.filters = filters;
	}

	next_page() {
		this.$item_list_title.html(this.title);
		const start = this.$list.find('.hub-item-wrapper').length;
		this.$loading.show();

		// build args
		let args = {
			start: start,
			// query one extra
			limit: this.page_length + 1
		};
		Object.assign(args, this.filters);
		console.log("filters: ", args);
		args.order_by = this.order_by;
		args.by_item_codes = this.by_item_codes;

		frappe.call({
			method: this.method,
			args: args,
			callback: (r) => {
				let items = r.message;
				console.log("items: ", items);
				this.render_items(items);
			}
		});
	}

	render_items(items) {
		if(items) {
			// clear any filler divs
			this.$list.find('.filler').remove();
			let done = 0;
			console.log("items length", items.length);
			if(items.length && items.length > this.page_length) {
				// remove the extra queried
				items.pop();
			} else {
				done = 1;
			}
			items.forEach((item) => {
				this.make_item_card(item).appendTo(this.$list);
			});

			const remainder = items.length % 4;
			if (remainder > 0) {
				// fill with filler divs to make flexbox happy
				Array.from(Array(remainder))
					.map(r => $('<div class="filler">').css('width', '200px').appendTo(this.$list));
			}
			this.update_list_state(done);
		} else {
			this.update_list_state(1);
		}
	}

	update_list_state(done=0) {
		this.$loading.hide();
		if(done) {
			this.$done.removeClass('hide');
			this.$more.hide();
		} else {
			this.$more.show();
			this.$done.addClass('hide');
		}
	}

	make_item_card(item) {
		let $item_card = $(`
			<div class="hub-item-wrapper" style="max-width: ${this.img_size}px;">
				<a class="item-link" href>
					<div class="hub-item-image">
						${ this.get_item_image(item) }
					</div>
					<div class="hub-item-title">
						<h5 class="bold">
							${!item.seen ? item.item_name : `<span class="indicator blue">${item.item_name}</span>`}
						<h5>
					</div>
				</a>
				<div class="company-link">
					<a data-company-name="${ item.company_name }" class="">${ item.company_name }</a>
				</div>
				<div>${ item.formatted_price ? item.formatted_price : ''}</div>
			</div>
		`);

		$item_card.find(".item-link").click((e) => {
			e.preventDefault();
			this.on_item_click && this.on_item_click(item.name);
		});

		return $item_card;
	}

	get_item_image(item, size=this.img_size) {
		const _size = size + 'px';
		const item_image = item.image ?
			`<img src="${item.image}"><span class="helper"></span>` :
			`<div class="standard-image">${item.item_name[0]}</div>`;

		return `
			<div class="img-wrapper"
				style="max-width: ${_size}; width: ${_size}; height: ${_size};">
				${item_image}
			</div>`;
	}
}
