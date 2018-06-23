frappe.provide('erpnext.hub');

erpnext.hub.HubListing = class HubListing extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.page_title = __('');
		this.method = 'erpnext.hub_node.get_list';

		this.cache = {};

		const route = frappe.get_route();
		this.page_name = route[1];

		this.menu_items = this.menu_items.concat(this.get_menu_items());

		this.imageFieldName = 'image';

		this.show_filters = 0;
	}

	set_title() {
		const title = this.page_title;
		let iconHtml = `<img class="hub-icon" src="assets/erpnext/images/hub_logo.svg">`;
		let titleHtml = `<span class="hub-page-title">${title}</span>`;
		this.page.set_title(iconHtml + titleHtml, '', false, title);
	}

	setup_fields() {
		return this.get_meta()
			.then(r => {
				this.meta = r.message.meta || this.meta;
				frappe.model.sync(this.meta);
				this.bootstrap_data(r.message);

				this.prepareFormFields();
			});
	}

	get_meta() {
		return new Promise(resolve =>
			frappe.call('erpnext.hub_node.get_meta', {doctype: this.doctype}, resolve));
	}

	set_breadcrumbs() { }

	prepareFormFields() { }

	bootstrap_data() { }

	get_menu_items() {
		const items = [
			{
				label: __('Hub Settings'),
				action: () => frappe.set_route('Form', 'Hub Settings'),
				standard: true
			},
			{
				label: __('Favourites'),
				action: () => frappe.set_route('Hub', 'Favourites'),
				standard: true
			}
		];

		return items;
	}

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.page.wrapper.find('.layout-side-section'),
			css_class: 'hub-sidebar'
		});
	}

	setup_sort_selector() {
		this.sort_selector = new frappe.ui.SortSelector({
			parent: this.filter_area.$filter_list_wrapper,
			doctype: this.doctype,
			args: this.order_by,
			onchange: () => this.refresh(true)
		});
	}

	setup_view() {
		if(frappe.route_options){
			const filters = [];
			for (let field in frappe.route_options) {
				var value = frappe.route_options[field];
				this.page.fields_dict[field].set_value(value);
			}
		}
	}

	get_args() {
		return {
			doctype: this.doctype,
			start: this.start,
			limit: this.page_length,
			order_by: this.order_by,
			// fields: this.fields,
			filters: this.get_filters_for_args()
		};
	}

	update_data(r) {
		const data = r.message;

		if (this.start === 0) {
			this.data = data;
		} else {
			this.data = this.data.concat(data);
		}

		this.data_dict = {};
	}

	freeze(toggle) { }

	render() {
		this.data_dict = {};
		this.render_image_view();

		this.setup_quick_view();
		this.setup_like();
	}

	render_offline_card() {
		let html = `<div class='page-card'>
			<div class='page-card-head'>
				<span class='indicator red'>
					{{ _("Payment Cancelled") }}</span>
			</div>
			<p>${ __("Your payment is cancelled.") }</p>
			<div><a href='' class='btn btn-primary btn-sm'>
				${ __("Continue") }</a></div>
		</div>`;

		let page = this.page.wrapper.find('.layout-side-section')
		page.append(html);

		return;
	}

	render_image_view() {
		var html = this.data.map(this.item_html.bind(this)).join("");

		if (this.start === 0) {
			// ${this.getHeaderHtml()}
			this.$result.html(`
				<div class="image-view-container small">
					${html}
				</div>
			`);
		}

		if(this.data.length) {
			this.doc = this.data[0];
		}

		this.data.map(this.loadImage.bind(this));

		this.data_dict = {};
		this.data.map(d => {
			this.data_dict[d.hub_item_code] = d;
		});
	}

	getHeaderHtml(title, image, content) {
		// let company_html =
		return `
			<header class="list-row-head text-muted small">
				<div style="display: flex;">
					<div class="list-header-icon">
						<img title="${title}" alt="${title}" src="${image}">
					</div>
					<div class="list-header-info">
						<h5>
							${title}
						</h5>
						<span class="margin-vertical-10 level-item">
							${content}
						</span>
					</div>
				</div>
			</header>
		`;
	}

	renderHeader() {
		return `<header class="level list-row-head text-muted small">
			<div class="level-left list-header-subject">
				<div class="list-row-col list-subject level ">
					<img title="Riadco%20Group" alt="Riadco Group" src="https://cdn.pbrd.co/images/HdaPxcg.png">
					<span class="level-item">Products by Blah blah</span>
				</div>
			</div>
			<div class="level-left checkbox-actions">
				<div class="level list-subject">
					<input class="level-item list-check-all hidden-xs" type="checkbox" title="${__("Select All")}">
					<span class="level-item list-header-meta"></span>
				</div>
			</div>
			<div class="level-right">
				${''}
			</div>
		</header>`;
	}

	get_image_html(encoded_name, src, alt_text) {
		return `<img data-name="${encoded_name}" src="${ src }" alt="${ alt_text }">`;
	}

	get_image_placeholder(title) {
		return `<span class="placeholder-text">${ frappe.get_abbr(title) }</span>`;
	}

	loadImage(item) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item[this.meta.title_field || 'name']);

		let placeholder = this.get_image_placeholder(title);
		let $container = this.$result.find(`.image-field[data-name="${encoded_name}"]`);

		if(!item[this.imageFieldName]) {
			$container.prepend(placeholder);
			$container.addClass('no-image');
		}

		frappe.load_image(item[this.imageFieldName],
			(imageObj) => {
				$container.prepend(imageObj)
			},
			() => {
				$container.prepend(placeholder);
				$container.addClass('no-image');
			},
			(imageObj) => {
				imageObj.title = encoded_name;
				imageObj.alt = title;
			}
		)
	}

	setup_quick_view() {
		if(this.quick_view) return;

		this.quick_view = new frappe.ui.Dialog({
			title: 'Quick View',
			fields: this.formFields
		});
		this.quick_view.set_primary_action(__('Request a Quote'), () => {
			this.show_rfq_modal()
				.then(values => {
					item.item_code = values.item_code;
					delete values.item_code;

					const supplier = values;
					return [item, supplier];
				})
				.then(([item, supplier]) => {
					return this.make_rfq(item, supplier, this.page.btn_primary);
				})
				.then(r => {
					console.log(r);
					if (r.message && r.message.rfq) {
						this.page.btn_primary.addClass('disabled').html(`<span><i class='fa fa-check'></i> ${__('Quote Requested')}</span>`);
					} else {
						throw r;
					}
				})
				.catch((e) => {
					console.log(e); //eslint-disable-line
				});
		}, 'octicon octicon-plus');

		this.$result.on('click', '.btn.zoom-view', (e) => {
			e.preventDefault();
			e.stopPropagation();
			var name = $(e.target).attr('data-name');
			name = decodeURIComponent(name);

			this.quick_view.set_title(name);
			let values = this.data_dict[name];
			this.quick_view.set_values(values);

			let fields = [];

			this.quick_view.show();

			return false;
		});
	}

	setup_like() {
		if(this.setup_like_done) return;
		this.setup_like_done = 1;
		this.$result.on('click', '.btn.like-button', (e) => {
			if($(e.target).hasClass('changing')) return;
			$(e.target).addClass('changing');

			e.preventDefault();
			e.stopPropagation();

			var name = $(e.target).attr('data-name');
			name = decodeURIComponent(name);
			let values = this.data_dict[name];

			let heart = $(e.target);
			if(heart.hasClass('like-button')) {
				heart = $(e.target).find('.octicon');
			}

			let remove = 1;

			if(heart.hasClass('liked')) {
				// unlike
				heart.removeClass('liked');
			} else {
				// like
				remove = 0;
				heart.addClass('liked');
			}

			frappe.call({
				method: 'erpnext.hub_node.update_wishlist_item',
				args: {
					item_name: values.hub_item_code,
					remove: remove
				},
				callback: (r) => {
					let message = __("Added to Favourites");
					if(remove) {
						message = __("Removed from Favourites");
					}
					frappe.show_alert(message);
				},
				freeze: true
			});

			$(e.target).removeClass('changing');
			return false;
		});
	}
}

erpnext.hub.ItemListing = class ItemListing extends erpnext.hub.HubListing {
	constructor(opts) {
		super(opts);
		this.show();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Item';
		this.page_title = __('Marketplace');
		this.fields = ['name', 'hub_item_code', 'image', 'item_name', 'item_code', 'company_name', 'description', 'country'];
		this.filters = [];
	}

	render() {
		this.data_dict = {};
		this.render_image_view();

		this.setup_quick_view();
		this.setup_like();
	}

	bootstrap_data(response) {
		let companies = response.companies.map(d => d.name);
		this.custom_filter_configs = [
			{
				fieldtype: 'Autocomplete',
				label: __('Select Company'),
				condition: 'like',
				fieldname: 'company_name',
				options: companies
			},
			{
				fieldtype: 'Link',
				label: __('Select Country'),
				options: 'Country',
				condition: 'like',
				fieldname: 'country'
			}
		];
	}

	prepareFormFields() {
		let fieldnames = ['item_name', 'description', 'company_name', 'country'];
		this.formFields = this.meta.fields
			.filter(field => fieldnames.includes(field.fieldname))
			.map(field => {
				let {
					label,
					fieldname,
					fieldtype,
				} = field;
				let read_only = 1;
				return {
					label,
					fieldname,
					fieldtype,
					read_only,
				};
			});

		this.formFields.unshift({
			label: 'image',
			fieldname: 'image',
			fieldtype: 'Attach Image'
		});
	}

	setup_side_bar() {
		super.setup_side_bar();

		let $pitch = $(`<div class="border" style="
				margin-top: 10px;
				padding: 0px 10px;
				border-radius: 3px;
			">
			<h5>Sell on HubMarket</h5>
			<p>Over 2000 products listed. Register your company to start selling.</p>
		</div>`);

		this.sidebar.$sidebar.append($pitch);

		this.category_tree = new frappe.ui.Tree({
			parent: this.sidebar.$sidebar,
			label: 'All Categories',
			expandable: true,

			args: {parent: this.current_category},
			method: 'erpnext.hub_node.get_categories',
			on_click: (node) => {
				this.update_category(node.label);
			}
		});

		this.sidebar.add_item({
			label: __('Companies'),
			on_click: () => frappe.set_route('Hub', 'Company')
		}, undefined, true);

		this.sidebar.add_item({
			label: this.hub_settings.company,
			on_click: () => frappe.set_route('Form', 'Company', this.hub_settings.company)
		}, __("Account"));

		this.sidebar.add_item({
			label: __("Favourites"),
			on_click: () => frappe.set_route('Hub', 'Favourites')
		}, __("Account"));

		this.sidebar.add_item({
			label: __("Settings"),
			on_click: () => frappe.set_route('Form', 'Hub Settings')
		}, __("Account"));
	}

	update_category(label) {
		this.current_category = (label=='All Categories') ? undefined : label;
		this.refresh();
	}

	get_filters_for_args() {
		if(!this.filter_area) return;
		let filters = {};
		this.filter_area.get().forEach(f => {
			let field = f[1] !== 'name' ? f[1] : 'item_name';
			filters[field] = [f[2], f[3]];
		});
		if(this.current_category) {
			filters['hub_category'] = this.current_category;
		}
		return filters;
	}

	update_data(r) {
		super.update_data(r);

		this.data_dict = {};
		this.data.map(d => {
			this.data_dict[d.hub_item_code] = d;
		});
	}

	item_html(item) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item[this.meta.title_field || 'name']);
		const _class = !item[this.imageFieldName] ? 'no-image' : '';
		const route = `#Hub/Item/${item.hub_item_code}`;
		const company_name = item['company_name'];

		const reviewLength = (item.reviews || []).length;
		const ratingAverage = reviewLength
			? item.reviews
				.map(r => r.rating)
				.reduce((a, b) => a + b, 0)/reviewLength
			: -1;

		let ratingHtml = ``;

		for(var i = 0; i < 5; i++) {
			let starClass = 'fa-star';
			if(i >= ratingAverage) starClass = 'fa-star-o';
			ratingHtml += `<i class='fa fa-fw ${starClass} star-icon' data-index=${i}></i>`;
		}

		let item_html = `
			<div class="image-view-item">
				<div class="image-view-header">
					<div class="list-row-col list-subject ellipsis level">
						<span class="level-item bold ellipsis" title="McGuffin">
							<a href="${route}">${title}</a>
						</span>
					</div>
					<div class="text-muted small" style="margin: 5px 0px;">
						${ratingHtml}
						(${reviewLength})
					</div>
					<div class="list-row-col">
						<a href="${'#Hub/Company/'+company_name+'/Items'}"><p>${ company_name }</p></a>
					</div>
				</div>
				<div class="image-view-body">
					<a  data-name="${encoded_name}"
						title="${encoded_name}"
						href="${route}"
					>
						<div class="image-field ${_class}"
							data-name="${encoded_name}"
						>
							<button class="btn btn-default zoom-view" data-name="${encoded_name}">
								<i class="octicon octicon-eye" data-name="${encoded_name}"></i>
							</button>
							<button class="btn btn-default like-button" data-name="${encoded_name}">
								<i class="octicon octicon-heart" data-name="${encoded_name}"></i>
							</button>
						</div>
					</a>
				</div>

			</div>
		`;

		return item_html;
	}

};

erpnext.hub.Favourites = class Favourites extends erpnext.hub.ItemListing {
	constructor(opts) {
		super(opts);
		this.show();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Item';
		this.page_title = __('Favourites');
		this.fields = ['name', 'hub_item_code', 'image', 'item_name', 'item_code', 'company_name', 'description', 'country'];
		this.filters = [];
		this.method = 'erpnext.hub_node.get_item_favourites';
	}

	setup_filter_area() { }

	setup_sort_selector() { }

	// setupHe

	getHeaderHtml() {
		return '';
	}

	get_args() {
		return {
			start: this.start,
			limit: this.page_length,
			order_by: this.order_by,
			fields: this.fields
		};
	}

	bootstrap_data(response) { }

	prepareFormFields() { }

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.page.wrapper.find('.layout-side-section'),
			css_class: 'hub-sidebar'
		});

		this.sidebar.add_item({
			label: __('Back to Products'),
			on_click: () => frappe.set_route('Hub', 'Item')
		});
	}

	update_category(label) {
		this.current_category = (label=='All Categories') ? undefined : label;
		this.refresh();
	}

	get_filters_for_args() {
		if(!this.filter_area) return;
		let filters = {};
		this.filter_area.get().forEach(f => {
			let field = f[1] !== 'name' ? f[1] : 'item_name';
			filters[field] = [f[2], f[3]];
		});
		if(this.current_category) {
			filters['hub_category'] = this.current_category;
		}
		return filters;
	}

	update_data(r) {
		super.update_data(r);

		this.data_dict = {};
		this.data.map(d => {
			this.data_dict[d.hub_item_code] = d;
		});
	}
};

erpnext.hub.CompanyListing = class CompanyListing extends erpnext.hub.HubListing {
	constructor(opts) {
		super(opts);
		this.show();
	}

	render() {
		this.data_dict = {};
		this.render_image_view();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Company';
		this.page_title = __('Companies');
		this.fields = ['company_logo', 'name', 'site_name', 'seller_city', 'seller_description', 'seller', 'country', 'company_name'];
		this.filters = [];
		this.custom_filter_configs = [
			{
				fieldtype: 'Link',
				label: 'Country',
				options: 'Country',
				condition: 'like',
				fieldname: 'country'
			}
		];
		this.imageFieldName = 'company_logo';
	}

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.page.wrapper.find('.layout-side-section'),
			css_class: 'hub-sidebar'
		});

		this.sidebar.add_item({
			label: __('Back to Products'),
			on_click: () => frappe.set_route('Hub', 'Item')
		});
	}

	get_filters_for_args() {
		let filters = {};
		this.filter_area.get().forEach(f => {
			let field = f[1] !== 'name' ? f[1] : 'company_name';
			filters[field] = [f[2], f[3]];
		});
		return filters;
	}

	item_html(company) {
		company._name = encodeURI(company.company_name);
		const encoded_name = company._name;
		const title = strip_html(company.company_name);
		const _class = !company[this.imageFieldName] ? 'no-image' : '';
		const company_name = company['company_name'];
		const route = `#Hub/Company/${company_name}`;

		let image_html = company.company_logo ?
			`<img src="${company.company_logo}"><span class="helper"></span>` :
			`<div class="standard-image">${frappe.get_abbr(company.company_name)}</div>`;

		let item_html = `
			<div class="image-view-item">
				<div class="image-view-header">
					<div class="list-row-col list-subject ellipsis level">
						<span class="level-item bold ellipsis" title="McGuffin">
							<a href="${route}">${title}</a>
						</span>
					</div>
				</div>
				<div class="image-view-body">
					<a  data-name="${encoded_name}"
						title="${encoded_name}"
						href="${route}">
						<div class="image-field ${_class}"
							data-name="${encoded_name}">
						</div>
					</a>
				</div>

			</div>
		`;

		return item_html;
	}

};