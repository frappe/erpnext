frappe.provide('erpnext.hub');

erpnext.hub.HubPage = class HubPage extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.page_title = __('Hub');
		this.method = 'erpnext.hub_node.get_items';

		const route = frappe.get_route();
		this.page_name = route[1];
	}

	setup_fields() {

	}

	set_breadcrumbs() {

	}

	setup_side_bar() {

	}

	setup_filter_area() {

	}

	setup_sort_selector() {

	}

	get_args() {
		return {
			start: this.start,
			limit: this.page_length,
			category: this.category || '',
			order_by: this.order_by,
			company: this.company || '',
			text: this.search_text || ''
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

	render() {
		this.render_image_view();
	}

	render_image_view() {
		var html = this.data.map(this.card_html.bind(this)).join("");

		this.$result.html(`
			<div class="image-view-container small">
				${html}
			</div>
		`);
	}

	card_html(item) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item['item_name' || 'item_code']);

		const _class = !item.image ? 'no-image' : '';
		const _html = item.image ?
			`<img data-name="${encoded_name}" src="${ item.image }" alt="${ title }">` :
			`<span class="placeholder-text">
				${ frappe.get_abbr(title) }
			</span>`;

		return `
			<div class="image-view-item">
				<div class="image-view-header">
					<div class="list-row-col list-subject ellipsis level">
						<div class="list-row-col">
							<span>${title}</span>
						</div>
					</div>
				</div>
				<div class="image-view-body">
					<a  data-name="${encoded_name}"
						title="${encoded_name}"
						href="#Hub/Item/${item.hub_item_code}"
					>
						<div class="image-field ${_class}"
							data-name="${encoded_name}"
						>
							${_html}
						</div>
					</a>
				</div>
			</div>
		`;
	}

	show_hub_form() {

	}
};
