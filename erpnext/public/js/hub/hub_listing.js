frappe.provide('erpnext.hub');

erpnext.hub.HubListing = class HubListing extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.page_title = __('Hub');
		this.method = 'erpnext.hub_node.get_list';

		this.cache = {};

		const route = frappe.get_route();
		this.page_name = route[1];
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

	setup_view() { }

	get_args() {
		return {
			doctype: this.doctype,
			start: this.start,
			limit: this.page_length,
			order_by: this.order_by,
			fields: this.fields,
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

	freeze(toggle) {
		// if(!this.$freeze) return;
		// this.$freeze.toggle(toggle);
		// if (this.$freeze.find('.image-view-container').length) return;

		// const html = Array.from(new Array(4)).map(d => this.card_html({
		// 	name: 'Loading...',
		// 	item_name: 'Loading...'
		// })).join('');

		// this.$freeze.html(`<div class="image-view-container border-top">${html}</div>`);
	}

	render() {
		this.data_dict = {};
		this.render_image_view();

		this.setup_quick_view();
	}

	render_image_view() {
		let data = this.data;
		if (this.start === 0) {
			this.$result.html('<div class="image-view-container small padding-top">');
			data = this.data.slice(this.start);
		}

		var html = data.map(this.card_html.bind(this)).join("");

		if(data.length) {
			this.doc = data[0];
		}

		this.$result.find('.image-view-container').append(html);
	}

	setup_quick_view() { }

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
		let $header_html = $(this.get_header_html());

		this.$result.html(`
			${this.get_header_html()}
			<div class="image-view-container small">
				${html}
			</div>
		`);

		this.data.map(this.load_image.bind(this));

		this.data_dict = {};
		this.data.map(d => {
			this.data_dict[d.hub_item_code] = d;
		});
	}

	get_header_html_skeleton(left = '', right = '') {
		return `
			<header class="level list-row list-row-head text-muted small">
				<div class="level-left list-header-subject">
					${left}
				</div>
				<div class="level-left checkbox-actions">
					<div class="level list-subject">
						<input class="level-item list-check-all hidden-xs" type="checkbox" title="${__("Select All")}">
						<span class="level-item list-header-meta"></span>
					</div>
				</div>
				<div class="level-right">
					${right}
				</div>
			</header>
		`;
	}

	get_header_html() {
		return this.get_header_html_skeleton(`
			<div class="list-row-col list-subject level ">
				<input class="level-item list-check-all hidden-xs" type="checkbox" title="Select All">
				<span class="level-item list-liked-by-me">
					<i class="octicon octicon-heart text-extra-muted" title="Likes"></i>
				</span>
				<span class="level-item"></span>
			</div>
		`);
	}

	get_image_html(encoded_name, src, alt_text) {
		return `<img data-name="${encoded_name}" src="${ src }" alt="${ alt_text }">`;
	}

	get_image_placeholder(title) {
		return `<span class="placeholder-text">${ frappe.get_abbr(title) }</span>`;
	}

	load_image(item) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item[this.meta.title_field || 'name']);
		const _class = !item.image ? 'no-image' : '';

		let placeholder = this.get_image_placeholder(title);
		let $container = this.$result.find(`.image-field[data-name="${encoded_name}"]`);

		if(!item.image) {
			$container.prepend(placeholder);
			// this.append_to_container(placeholder, );
		}

		let $container = this.$result.find(`.image-field[data-name="${encoded_name}"]`)

		let placeholder = this.get_image_placeholder(title);

		this.is_image_loaded(item.image, title, encoded_name, this.append_to_container)
	}

	is_image_loaded(src, alt_text, encoded_name, onload, onerror) {
		var me = this;
		let $container = this.$result.find(`.image-field[data-name="${encoded_name}"]`);
		var tester = new Image();
		tester.onload = function() {
			$container.prepend(this);
		};
		tester.onerror= function() {
			let placeholder = me.get_image_placeholder(alt_text);
			$container.prepend(placeholder);
			$container.addClass('no-image');
		};
		tester.encoded_name = encoded_name;
		tester.alt_text = alt_text;
		tester.src = src;
	}

	item_html(item) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item[this.meta.title_field || 'name']);
		const _class = !item.image ? 'no-image' : '';
		const route = `#Hub/Item/${item.hub_item_code}`;
		const company_name = item['company_name'];

		let item_html = `
			<div class="image-view-item">

				<div class="image-view-header">
					<div class="list-row-col list-subject ellipsis level">
						<span class="level-item bold ellipsis" title="McGuffin">
							<a href="${route}">${title}</a>
						</span>
					</div>
					<div class="list-row-col">
						<a href="${'#Hub/Company/'+company_name}"><p>${ company_name }</p></a>
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

}

erpnext.hub.ItemListing = class ItemListing extends erpnext.hub.HubListing {
	constructor(opts) {
		super(opts);
		this.show();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Item';
		this.fields = ['name', 'hub_item_code', 'image', 'item_name', 'item_code', 'company_name'];
		this.filters = [];
	}

	setup_sort_selector() {
		//
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
		let fieldnames = ['hub_item_code', 'item_name', 'item_code', 'description',
			'seller', 'company_name', 'country'];
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
			label: 'Category',
			fieldname: 'hub_category',
			fieldtype: 'Data'
		});

		this.formFields.unshift({
			label: 'image',
			fieldname: 'image',
			fieldtype: 'Attach Image'
		});
	}

	setup_side_bar() {
		super.setup_side_bar();
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
		});

		this.sidebar.add_item({
			label: this.hub_settings.company,
			on_click: () => frappe.set_route('Form', 'Company', this.hub_settings.company)
		}, __("Account"));

		this.sidebar.add_item({
			label: __("My Orders"),
			on_click: () => frappe.set_route('List', 'Request for Quotation')
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


	setup_quick_view() {
		if(this.quick_view) return;

		this.quick_view = new frappe.ui.Dialog({
			title: 'Quick View',
			fields: this.formFields
		});
		this.$result.on('click', '.btn.zoom-view', (e) => {
			e.preventDefault();
			e.stopPropagation();
			var name = $(e.target).attr('data-name');
			name = decodeURIComponent(name);

			this.quick_view.set_title(name);
			let values = this.data_dict[name];
			this.quick_view.set_values(values);

			let fields = [];

			this.quick_view.set_primary_action('Send', () => {
				let category = this.quick_view.get_values().hub_category;
				return new Promise((resolve, reject) => {
					frappe.call({
						method: 'erpnext.hub_node.update_category',
						args: {
							hub_item_code: values.hub_item_code,
							category: category,
						},
						callback: (r) => {
							resolve();
						},
						freeze: true
					}).fail(reject);
				});
			});
			this.quick_view.show();

			return false;
		});
	}
};

erpnext.hub.CompanyListing = class CompanyListing extends erpnext.hub.HubListing {
	constructor(opts) {
		super(opts);
		this.show();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Company';
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
	}

	get_filters_for_args() {
		let filters = {};
		this.filter_area.get().forEach(f => {
			let field = f[1] !== 'name' ? f[1] : 'company_name';
			filters[field] = [f[2], f[3]];
		});
		return filters;
	}

	card_html(company) {
		company._name = encodeURI(company.name);
		const route = `#Hub/Company/${company.company_name}`;

		let image_html = company.company_logo ?
			`<img src="${company.company_logo}"><span class="helper"></span>` :
			`<div class="standard-image">${frappe.get_abbr(company.company_name)}</div>`;

		return `
			<div class="hub-item-wrapper margin-bottom" style="width: 200px;">
				<a href="${route}">
					<div class="hub-item-image">
						<div class="img-wrapper" style="height: 200px; width: 200px">
							${ image_html }
						</div>
					</div>
					<div class="hub-item-title">
						<h5 class="bold">
							${ company.company_name }
						</h5>
					</div>
				</a>
			</div>
		`;
	}
};