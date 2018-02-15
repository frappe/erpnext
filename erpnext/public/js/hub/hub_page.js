frappe.provide('erpnext.hub');

erpnext.hub.HubListing = class HubListing extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.page_title = __('Hub');
		this.method = 'erpnext.hub_node.get_list';

		const route = frappe.get_route();
		this.page_name = route[1];
	}

	setup_fields() {
		return this.get_meta()
			.then(r => {
				this.meta = r.message || this.meta;
				frappe.model.sync(this.meta);
			});
	}

	get_meta() {
		return new Promise(resolve =>
			frappe.call('erpnext.hub_node.get_meta', {doctype: this.doctype}, resolve));
	}

	set_breadcrumbs() { }

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.page.wrapper.find('.layout-side-section'),
			css_class: 'hub-sidebar'
		});
	}

	setup_sort_selector() { }

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

	}

	freeze(toggle) {
		this.$freeze.toggle(toggle);
		if (this.$freeze.find('.image-view-container').length) return;

		const html = Array.from(new Array(4)).map(d => this.card_html({
			name: 'Loading...',
			item_name: 'Loading...'
		})).join('');

		this.$freeze.html(`<div class="image-view-container border-top">${html}</div>`);
	}

	render() {
		this.render_image_view();
	}

	render_image_view() {
		let data = this.data;
		if (this.start === 0) {
			this.$result.html('<div class="image-view-container small padding-top">');
			data = this.data.slice(this.start);
		}

		var html = data.map(this.card_html.bind(this)).join("");
		this.$result.find('.image-view-container').append(html);
	}
}

erpnext.hub.ItemListing = class ItemListing extends erpnext.hub.HubListing {
	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Item';
		this.fields = ['name', 'hub_item_code', 'image', 'item_name', 'item_code', 'company_name'];
		this.filters = [];
		this.custom_filter_configs = [
			{
				fieldtype: 'Data',
				label: 'Company',
				condition: 'like',
				fieldname: 'company_name',
			},
			{
				fieldtype: 'Link',
				label: 'Country',
				options: 'Country',
				condition: 'like',
				fieldname: 'country'
			}
		];
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

	card_html(item) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item['item_name' || 'item_code']);
		const company_name = item['company_name'];

		const route = `#Hub/Item/${item.hub_item_code}`;

		const image_html = item.image ?
			`<img src="${item.image}">
			<span class="helper"></span>` :
			`<div class="standard-image">${frappe.get_abbr(title)}</div>`;

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
							${ title }
						</h5>

					</div>
				</a>
				<a href="${'#Hub/Company/'+company_name}"><p>${ company_name }</p></a>
			</div>
		`;
	}
};

erpnext.hub.CompanyListing = class CompanyListing extends erpnext.hub.HubListing {
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