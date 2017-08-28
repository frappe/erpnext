/* globals ERPNextHub, ERPNextHubList */

frappe.provide('erpnext.hub');

frappe.pages['hub'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'ERPNext Hub'
	});

	erpnext.hub.Hub = new ERPNextHub({ page });
};

window.ERPNextHub = class ERPNextHub {
	constructor({ page }) {
		this.page = page;

		frappe.require('/assets/erpnext/css/hub.css',
			() => this.setup()
		);
	}

	setup() {
		this.setup_header();
		this.$hub_main_section =
			$(`<div class='hub-main-section'>`).appendTo(this.page.body);
		this.refresh();
	}

	refresh() {
		this.$hub_main_section.empty();
		this.page.page_form.hide();

		frappe.model.with_doc('Hub Settings', 'Hub Settings', () => {
			this.hub_settings = frappe.get_doc('Hub Settings');
			if(!this.hub_settings.enabled) {
				this.setup_empty_state();
			} else {
				this.setup_live_state();
			}
		});
	}

	setup_header() {
		this.page.page_title = this.page.wrapper.find('.page-title');
		this.tag_line = $(`
			<div class='tag-line-container'>
				<span class='tag-line text-muted small'>
					Product listing and discovery for ERPNext users
				</span>
			</div>`)
			.appendTo(this.page.page_title);

		this.account_details = $(`
			<div class='account-details text-muted'>
				<!-- <i class='octicon octicon-person'></i> <a class='user-name small'></a> -->
				<i class='octicon octicon-globe' style='margin-left: 20px;'></i> <a class='company-name small'></a>
			</div>`)
			.appendTo(this.page.page_actions)
			.hide();

		this.bind_title();
	}

	setup_empty_state() {
		this.remove_account_from_header();
		let $empty_state = $(`
			<div style="padding: 70px 0px;">
				<h2 class="text-center">${ __("Register For ERPNext Hub") }</h2>
				<br>
				<div class="row">
					<div class="col-md-6 col-md-offset-3">
						<ul>
							<li>Let other ERPNext users discover your products</li>
							<li>Automate workflow with Supplier from within ERPNext (later)</li>
						</ul>
					</div>
				</div>
				<br>
				<div class="text-center">
					<a class="btn btn-primary hub-settings-btn">Hub Settings</a>
				</div>
			</div>
		`);
		this.$hub_main_section.append($empty_state);
		this.$hub_main_section.find('.hub-settings-btn').on('click', () => {
			frappe.set_route('Form', 'Hub Settings', {});
		});
	}

	setup_live_state() {
		this.add_account_to_header();
		if(!this.$search) {
			this.setup_filters();
		}
		this.page.page_form.show();
		this.render_body();
		this.setup_lists();
	}

	setup_filters() {
		let categories = this.get_hub_categories().map(d => {
			return {label: __(d), value: d}
		});
		let countries = this.get_hub_countries().map(d => {
			return {label: d, value: d}
		});

		this.category_select = this.page.add_select(__('Category'),
			[{'label': __('Select Category...'), value: '' }].concat(categories)
		);
		this.country_select = this.page.add_select(__('Country'),
			[{'label': __('Select Country...'), value: '' }].concat(countries)
		);

		this.get_hub_companies((companies) => {
			let company_names = companies.map(d => {
				return {label: d.company, value: d.company}
			});

			this.company_select = this.page.add_select(__('Company'),
				[{'label': __('Select Company...'), value: '' }].concat(company_names)
			);

			this.company_select.on('change', () => {
				this.$search.val('');
				let val = $(this.company_select).val() || '';
				this.go_to_items_only_page(
					['hub', 'Company', val, 'Products'],
					'Products by '  + val,
					'company-product-list',
					{text: '', company: val}
				);
			});
		});

		this.$search = this.page.add_data(__('Search'));
		this.bind_filters();
		this.setup_search();
	}

	bind_filters() {
		// TODO: categories
		// bind dynamically
	}

	reset_filters() {
		$(this.company_select).val('');
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
			filters: {text: ''}, // filters at the time of creation
			on_item_click: (item) => {
				this.go_to_item_page(item);
			}
		});

		this.home_item_list.setup();

		this.setup_company_list();
	}

	setup_company_list() {
		this.get_hub_companies((companies) => {
			companies.map(company => {
				let company_card = $(`<div class='company_card'>
				</div>`).appendTo(this.$side_list_section);
			});
		})
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

	go_to_items_only_page(route, title, class_name, filters) {
		frappe.set_route(route);
		this.$hub_main_section.empty();
		this.filtered_item_list = new ERPNextHubList({
			parent: this.$hub_main_section,
			title: title,
			page_length: 20,
			list_css_class: class_name,
			method: 'erpnext.hub_node.get_items',
			filters: filters
		});
		this.filtered_item_list.on_item_click = (item) => {
			this.go_to_item_page(item);
		}
		this.filtered_item_list.setup();
	}

	go_to_item_page(item) {
		// TODO: Check if item quote already requested
		frappe.set_route('hub', 'Item', item.item_name);
		this.$hub_main_section.empty();

		let $item_page =
			$(this.get_item_page(item))
				.appendTo(this.$hub_main_section);

		let $company_items = $item_page.find('.company-items');

		let company_item_list = new ERPNextHubList({
			parent: $company_items,
			title: 'More by ' + item.company,
			page_length: 5,
			list_css_class: 'company-item-list',
			method: 'erpnext.hub_node.get_items',
			filters: {text: '', company: item.company},
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

		// let $breadcrumbs = $();
		// $item_page.prepend($breadcrumbs);
		// this.bind_breadcrumbs();
	}

	get_item_page(item) {
		return `
			<div class="hub-item-page">
				<div class="item-header">
					<div class="item-page-image">
						<img src="${ item.image }">
					</div>
					<div class="title-content">
						<div class="title">
							<h2>${ item.item_name }</h2>
						</div>
						<div class="company">
							<span class="">${ item.company }</span>
						</div>
						<div class="category">
							<span class="text-muted">Products</span>
						</div>
						<div class="description">
							<span class="small">${ item.description }</span>
						</div>
						<div class="price">
							${ item.standard_rate ? format_currency(item.standard_rate) : '' }
						</div>
						<div class="actions">
							<a class="btn btn-primary rfq-btn">Request A Quote</a>
						</div>
					</div>

				</div>
				<div class="item-more-info"></div>
				<div class="company-items">
					<!--<div class="title">
						More by ${ item.company }
					</div>
					<div class="company-item-list">
					</div>-->
				</div>
			</div>
		`;
	}

	go_to_company_page(company) {
		frappe.set_route('hub', 'Company', company.name);
	}

	// bind_breadcrumbs() {}

	go_to_home_page() {
		frappe.set_route('hub');
		this.reset_filters();
		this.refresh();
	}

	add_account_to_header() {
		const { hub_user_name, company } = this.hub_settings;
		// this.account_details.find('.user-name').hide();
		this.account_details.find('.company-name').text(company);
		this.account_details.show();
	}

	remove_account_from_header() {
		this.account_details.hide();
	}

	get_hub_categories(callback) {
		// frappe.call({
		// 	method: "erpnext.hub_node.get_all_categories",
		// 	args: {},
		// 	callback: function(r) {
		// 		let categories = r.message.categories ? r.message.categories : [];
		// 		callback(categories);
		// 	}
		// });
		return [];
	}
	get_hub_countries(callback) {
		return [];
	}
	get_hub_companies(callback) {
		frappe.call({
			method: 'erpnext.hub_node.get_all_companies',
			args: {},
			callback: function(r) {
				let companies = r.message.companies ? r.message.companies : [];
				callback(companies);
			}
		});
	}

	get_search_term() {
		return this.$search.val();
	}

	make_rfq(item, callback) {
		// should be through hub?
		frappe.call({
			method: 'erpnext.hub_node.make_rfq_and_send_opportunity',
			args: {
				item_code: item.item_code,
				item_group: 'Products',
				supplier_name: item.hub_user_name,
				supplier_email: item.hub_user_email,
				company: item.company,
				country: item.country
			},
			callback: function(r) {
				callback(r.message);
			}
		});
	}
}

window.ERPNextHubList = class ERPNextHubList {
	constructor({
		parent = null,
		title = 'Items',
		page_length = 10,
		list_css_class = '',
		method = '',
		filters = {text: ''},
		on_item_click = null,
		img_size = 200
	}) {
		this.parent = parent;
		this.title = title;
		this.page_length = page_length;
		this.list_css_class = list_css_class;
		this.method = method;
		this.filters = filters;
		this.on_item_click = on_item_click;
		this.img_size = img_size;
		// this.setup();
	}

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
		const me = this;
		this.$item_list_title.html(this.title);
		const start = this.$list.find('.hub-item-wrapper').length;
		this.$loading.show();

		// build args
		let args = {
			start: start,
			limit: this.page_length + 1
		};
		Object.assign(args, this.filters);

		frappe.call({
			method: this.method,
			args: args,
			callback: function(r) {
				let items = r.message.items;
				console.log("items: ", items);
				me.$loading.hide();
				if(items) {
					if(items.length && items.length > me.page_length) {
						items.pop();
						me.$more.show();
						me.$done.addClass('hide');
					} else {
						this.$done.removeClass('hide');
						this.$more.hide();
					}
					items.forEach(function(item) {
						me.make_item_card(item).appendTo(me.$list);
					});
				} else {
					this.$item_list_title.html('No results found');
				}
			}
		});
	}

	make_item_card(item) {
		return $(`
			<div class="hub-item-wrapper" style="max-width: ${this.img_size}px;">
				<a href>
					<div class="hub-item-image">
						${ this.get_item_image(item) }
					</div>
					<div class="hub-item-title">
						<h5 class="bold">
							${item.item_name}
						<h5>
					</div>
				</a>
				<div>${ item.company }</div>
				<div>${ item.standard_rate ? format_currency(item.standard_rate) : ''}</div>
			</div>
		`).click((e) => {
			e.preventDefault();
			this.on_item_click && this.on_item_click(item);
		});
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
};
