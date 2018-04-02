frappe.provide('erpnext.hub');

erpnext.hub.HubForm = class HubForm extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.method = 'erpnext.hub_node.get_details';
		const route = frappe.get_route();
		this.page_name = route[2];
	}

	set_breadcrumbs() {
		frappe.breadcrumbs.add({
			label: __('Hub'),
			route: '#Hub/' + this.doctype,
			type: 'Custom'
		});
	}

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.$page.find('.layout-side-section'),
			css_class: 'hub-form-sidebar'
		});
	}

	setup_filter_area() { }

	setup_sort_selector() { }

	get_args() {
		return {
			hub_sync_id: this.unique_id,
			doctype: 'Hub ' + this.doctype
		};
	}

	prepare_data(r) {
		this.data = r.message;
	}

	update_data(r) {
		this.data = r.message;
	}

	render() {
		const image_html = this.data[this.image_field_name] ?
			`<img src="${this.data[this.image_field_name]}">
			<span class="helper"></span>` :
			`<div class="standard-image">${frappe.get_abbr(this.page_title)}</div>`;

		this.sidebar.add_item({
			label: image_html
		});

		let fields = this.get_field_configs();

		this.form = new frappe.ui.FieldGroup({
			parent: this.$result,
			fields
		});

		this.form.make();
		this.form.set_values(this.data);
	}

	toggle_result_area() {
		this.$result.toggle(this.unique_id);
		this.$paging_area.toggle(this.data.length > 0);
		this.$no_result.toggle(this.data.length == 0);

		const show_more = (this.start + this.page_length) <= this.data.length;
		this.$paging_area.find('.btn-more')
			.toggle(show_more);
	}
};

erpnext.hub.ItemPage = class ItemPage extends erpnext.hub.HubForm{
	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Item';
		this.image_field_name = 'image';
	}

	get_field_configs() {
		let fields = [];
		this.fields.map(fieldname => {
			fields.push({
				label: toTitle(frappe.model.unscrub(fieldname)),
				fieldname,
				fieldtype: 'Data',
				read_only: 1
			});
		});

		let category_field = {
			label: 'Hub Category',
			fieldname: 'hub_category',
			fieldtype: 'Data'
		}

		if(this.data.company_name === this.hub_settings.company) {
			this.page.set_primary_action(__('Update'), () => {
				this.update_on_hub();
			}, 'octicon octicon-plus');
		} else {
			category_field.read_only = 1;
		}

		fields.unshift(category_field);

		return fields;
	}

	update_on_hub() {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: 'erpnext.hub_node.update_category',
				args: { item: this.unique_id, category: this.form.get_value('hub_category') },
				callback: resolve,
				freeze: true
			}).fail(reject);
		});
	}

	setup_fields() {
		this.fields = ['hub_item_code', 'item_name', 'item_code', 'description',
			'seller', 'company_name', 'country'];
	}
}

erpnext.hub.CompanyPage = class CompanyPage extends erpnext.hub.HubForm{
	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Company';
		this.image_field_name = 'company_logo';
	}

	get_field_configs() {
		let fields = [];
		this.fields.map(fieldname => {
			fields.push({
				label: toTitle(frappe.model.unscrub(fieldname)),
				fieldname,
				fieldtype: 'Data',
				read_only: 1
			});
		});

		return fields;
	}

	setup_fields() {
		this.fields = ['company_name', 'description', 'route', 'country', 'seller', 'site_name'];
	}
}
