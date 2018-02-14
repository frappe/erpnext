frappe.provide('erpnext.hub');

erpnext.hub.HubForm = class HubForm extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.method = 'erpnext.hub_node.get_details';
		//doctype, unique_id,
	}

	set_breadcrumbs() {
		this.set_title();
		frappe.breadcrumbs.add({
			label: __('Hub'),
			route: '#Hub/' + this.doctype,
			type: 'Custom'
		});
	}

	set_title() {
		this.page_title = this.data.item_name || this.hub_item_code || 'Hub' + this.doctype;
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

		let fields = [];
		this.fields.map(fieldname => {
			fields.push({
				label: toTitle(frappe.model.unscrub(fieldname)),
				fieldname,
				fieldtype: 'Data',
				read_only: 1
			});
		});

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

	setup_fields() {
		this.fields = ['hub_item_code', 'item_name', 'item_code', 'description',
			'seller', 'company_name', 'country', 'hub_category'];
	}

	show_action_modal(item) {
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
}

erpnext.hub.CompanyPage = class CompanyPage extends erpnext.hub.HubForm{
	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Company';
		this.image_field_name = 'company_logo';
	}

	setup_fields() {
		this.fields = ['company_name', 'description', 'route', 'country', 'seller', 'site_name'];
	}
}
