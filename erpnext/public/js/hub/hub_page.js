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
				console.log('fields then', this.doctype);
				this.meta = r.message || this.meta;
				frappe.model.sync(this.meta);
			});
	}

	get_meta() {
		console.log('get_meta', this.doctype);
		return new Promise(resolve =>
			frappe.call('erpnext.hub_node.get_meta', {doctype: this.doctype}, resolve));
	}

	set_breadcrumbs() { }

	setup_side_bar() { }

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
		console.log('update data', data);

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
		// console.log('this.data render', this.data);
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
		// console.log(item);
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
							${image_html}
						</div>
					</div>
					<div class="hub-item-title">
						<h5 class="bold">
							${ title }
						</h5>
						<p>${ company_name }</p>
					</div>
				</a>
			</div>
		`;
	}
};

erpnext.hub.CompanyListing = class CompanyListing extends erpnext.hub.HubListing {
	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Company';
		this.fields = ['name', 'site_name', 'seller_city', 'seller_description', 'seller', 'country', 'company_name'];
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

	get_filters_for_args() {
		let filters = {};
		this.filter_area.get().forEach(f => {
			let field = f[1] !== 'name' ? f[1] : 'company_name';
			filters[field] = [f[2], f[3]];
		});
		return filters;
	}

	card_html(item) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item['item_name' || 'item_code']);
		// console.log(item);
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
							${image_html}
						</div>
					</div>
					<div class="hub-item-title">
						<h5 class="bold">
							${ title }
						</h5>
						<p>${ company_name }</p>
					</div>
				</a>
			</div>
		`;
	}
};