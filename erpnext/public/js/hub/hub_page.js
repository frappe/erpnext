frappe.provide('erpnext.hub');

erpnext.hub.HubPage = class HubPage extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.page_title = __('Hub');
		this.method = 'erpnext.hub_node.get_items';

		const route = frappe.get_route();
		this.page_name = route[1];

		return this.get_hub_item_meta()
			.then(r => {
				this.meta = r.message || this.meta;
				this.doctype = 'Hub Item';
				frappe.model.sync(this.meta);
			});
	}

	get_hub_item_meta() {
		return new Promise(resolve =>
			frappe.call('erpnext.hub_node.get_hub_item_meta', {}, resolve));
	}

	setup_fields() {
		this.fields = ['name', 'hub_item_code', 'image', 'item_name', 'item_code'];
	}

	set_breadcrumbs() {

	}

	setup_side_bar() {

	}

	setup_filter_area() {
		this.filter_area = new FilterArea(this);
	}

	setup_sort_selector() {

	}

	setup_view() {

	}

	get_args() {
		return {
			start: this.start,
			limit: this.page_length,
			category: this.category || '',
			order_by: this.order_by,
			company: this.company || '',
			text: this.search_text || '',
			fields: this.fields
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
			name: 'freeze',
			item_name: 'freeze'
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

	card_html(item) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item['item_name' || 'item_code']);

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
					</div>
				</a>
			</div>
		`;
	}
};