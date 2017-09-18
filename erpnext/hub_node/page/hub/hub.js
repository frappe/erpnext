/* globals ERPNextHub, ERPNextHubList */

frappe.provide('erpnext.hub');

frappe.pages['hub'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Hub',
		single_col: false
	});

	erpnext.hub.Hub = new ERPNextHub({ page });

};

frappe.pages['hub'].on_page_show = function(wrapper) {
	const current_route = frappe.get_route();

	// if(current_route[1] === "Products") {
	// 	if(current_route[2]) {
	// 		const item_code = current_route[2];
	// 	}
	// }

	if(current_route[1] === "Company") {
		if(current_route[2]) {
			// erpnext.hub.Hub.refresh();
			erpnext.hub.Hub.get_company_details(current_route[2]);
		}
	}
}

window.ERPNextHub = class ERPNextHub {
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

		frappe.model.with_doc('Hub Settings', 'Hub Settings', () => {
			this.hub_settings = frappe.get_doc('Hub Settings');

			if(this.hub_settings.enabled == 0) {
				let $empty_state = this.page.get_empty_state(
					__("Register for Hub"),
					__(`Let other ERPNext users discover your products
						and automate workflow with Supplier from within ERPNext.`),
					__("Register")
				);

				$layout_main
					.find('.layout-side-section, .layout-main-section-wrapper')
					.hide();
				$layout_main.append($empty_state);

				$empty_state.find('.btn-primary').on('click', () => {
					// frappe.set_route('Form', 'Hub Settings');
					this.register_for_hub();
				});
			} else {
				$layout_main.find('.page-card-container').remove();
				$layout_main.find('.layout-side-section, .layout-main-section-wrapper').show();
				this.setup_live_state();
			}
		});
	}

	register_for_hub() {
		frappe.verify_password(() => {
			frappe.call({
				method: 'erpnext.hub_node.enable_hub',
				callback: (r) => {
					if(r.message.enabled == 1) {
						Object.assign(this.hub_settings, r.message);
						this.refresh();
					}
				}
			});
		});
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

		this.$search = this.page.add_data(__('Search'));
		this.setup_search();
	}

	bind_events() {
		const me = this;
		this.$hub_main_section
			.on('click', '.company-link a', function(e) {
				e.preventDefault();
				const company_name = $(this).attr('data-company-name');
				me.get_company_details(company_name);
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
		this.home_item_list = new ERPNextHubList({
			parent: this.$main_list_section,
			title: 'New',
			page_length: 20,
			list_css_class: 'home-product-list',
			method: 'erpnext.hub_node.get_items',
			// order_by: 'request_count',
			filters: {text: '', country: this.country}, // filters at the time of creation
			on_item_click: (item) => {
				this.go_to_item_page(item);
			}
		});

		this.home_item_list.setup();
	}

	setup_search() {
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
		this.filtered_item_list = new ERPNextHubList({
			parent: this.$hub_main_section,
			title: title,
			page_length: 20,
			list_css_class: class_name,
			method: 'erpnext.hub_node.get_items',
			order_by: this.order_by,
			filters: filters,
			by_item_codes: by_item_codes
		});
		this.filtered_item_list.on_item_click = (item) => {
			this.go_to_item_page(item);
		}
		this.filtered_item_list.setup();
	}

	go_to_item_page(item) {
		frappe.set_route('hub', 'Products', item.item_name);
		this.$hub_main_section.empty();

		let $item_page =
			$(this.get_item_page(item))
				.appendTo(this.$hub_main_section);

		let $company_items = $item_page.find('.company-items');

		let company_item_list = new ERPNextHubList({
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

		company_item_list.on_item_click = (item) => {
			this.go_to_item_page(item);
		}
		company_item_list.setup();

		let $rfq_btn = $item_page.find('.rfq-btn');
		$rfq_btn.on('click', () => {
			$rfq_btn.addClass('disabled');
			this.make_rfq(item, (success) => {
				if(success) {
					$rfq_btn.html(`<span><i class='fa fa-check'></i> Quote Requested</span>`);
				} else {
					frappe.msgprint(__('Sorry, we cannot process your request at this time.'));
				}
			});
		});
	}

	get_company_details(company_id) {
		// get from cache if exists
		// let company_details = this.company_cache[company_id];
		// if(this.company_cache[company_id]) {
		// 	this.go_to_company_page(company_details);
		// 	return;
		// }
		// frappe.call({
		// 	method: 'erpnext.hub_node.get_company_details',
		// 	args: {company_id: company_id}
		// }).then((r) => {
		// 	if (r.message) {
		// 		const company_details = r.message.company_details;
		// 		this.company_cache[company_id] = company_details;
		// 		this.go_to_company_page(company_details)
		// 	}
		// });
	}

	go_to_company_page(company_details) {
		frappe.set_route('hub', 'Company', company_details.company_name);
		this.$hub_main_section.empty();

		let $company_page =
			$(this.get_company_page(company_details))
				.appendTo(this.$hub_main_section);

		let $company_items = $company_page.find('.company-items');

		let company_item_list = new ERPNextHubList({
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

		company_item_list.on_item_click = (item) => {
			this.go_to_item_page(item);
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
							<span class="small">${ item.description }</span>
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
							<span class="">${ company_details.seller_city }</span>
						</div>
						<div class="description">
							<span class="small">${ company_details.seller_description }</span>
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
		this.page.add_menu_item(__('Hub Settings'),
			() => frappe.set_route('Form', 'Hub Settings'));

		this.page.add_menu_item(__('Refresh'), () => this.refresh());
	}

	setup_sidebar() {
		var me = this;
		this.sidebar = new ERPNextHubSidebar({
			wrapper: this.page.wrapper.find('.layout-side-section')
		});

		this.add_account_to_sidebar();

	}

	add_account_to_sidebar() {
		this.sidebar.add_item({
			label: this.hub_settings.company,
			on_click: () => frappe.set_route('Form', 'Company', this.hub_settings.company)
		}, __("Account"));

		this.sidebar.add_item({
			label: __("Requested Products"),
			on_click: () => this.go_to_seen_items()
		}, __("Account"));
	}

	get_search_term() {
		return this.$search.val();
	}

	reset_search() {
		this.$search.val('');
	}

	make_rfq(item, callback) {
		frappe.call({
			method: 'erpnext.hub_node.hub_item_request_action',
			args: {
				item_code: item.item_code,
				item_group: 'Products',
				supplier_name: item.hub_user_name,
				supplier_email: item.hub_user_email,
				company: item.company_name,
				country: item.country
			},
			callback: (r) => {
				callback(r.message);
			}
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

class ERPNextHubList {
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
			console.log(done);
			this.update_list_state(done);
		} else {
			this.$item_list_title.html('No results found');
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
					<a data-company-name="${ item.company_id }" class="">${ item.company_name }</a>
				</div>
				<div>${ item.formatted_price ? item.formatted_price : ''}</div>
			</div>
		`);

		$item_card.find(".item-link").click((e) => {
			e.preventDefault();
			this.on_item_click && this.on_item_click(item);
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

class ERPNextHubSidebar {
	constructor({ wrapper }) {
		this.wrapper = wrapper;
		this.make_dom();
	}

	make_dom() {
		this.wrapper.html(`
			<div class="hub-sidebar overlay-sidebar hidden-xs hidden-sm">
			</div>
		`);

		this.$sidebar = this.wrapper.find('.hub-sidebar');
	}

	add_item(item, section) {
		let $section;
		if(!section && this.wrapper.find('.sidebar-menu').length === 0) {
			// if no section, add section with no heading
			$section = this.get_section();
		} else {
			$section = this.get_section(section);
		}

		const $li_item = $(`
			<li><a ${item.href ? `href="${item.href}"` : ''}>${item.label}</a></li>
		`).click(
			() => item.on_click && item.on_click()
		);

		$section.append($li_item);
	}

	get_section(section_heading="") {
		let $section = $(this.wrapper.find(
			`[data-section-heading="${section_heading}"]`));
		if($section.length) {
			return $section;
		}

		const $section_heading = section_heading ?
			`<li class="h6">${section_heading}</li>` : '';

		$section = $(`
			<ul class="list-unstyled sidebar-menu" data-section-heading="${section_heading || 'default'}">
				${$section_heading}
			</ul>
		`);

		this.$sidebar.append($section);
		return $section;
	}
}