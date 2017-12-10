frappe.provide('erpnext.hub');

erpnext.hub.HubForm = class HubForm extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.page_title = this.data.item_name || this.hub_item_code || __('Hub Item');
		this.method = 'erpnext.hub_node.get_item_details';
	}

	setup_fields() {

	}

	set_breadcrumbs() {
		frappe.breadcrumbs.add({
			label: __('Hub'),
			route: '#Hub/Item',
			type: 'Custom'
		});
	}

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.$page.find('.layout-side-section'),
			css_class: 'hub-form-sidebar'
		});
	}

	setup_filter_area() {

	}

	setup_sort_selector() {

	}

	get_args() {
		return {
			hub_sync_id: this.hub_item_code
		};
	}

	update_data(r) {
		const data = r.message;
		this.data = data;
	}

	render() {
		this.sidebar.add_item({
			label: `<img src="${this.data.image}" />`
		});

		let fields = [];
		for (let fieldname in this.data) {
			fields.push({
				label: toTitle(fieldname),
				fieldname,
				fieldtype: 'Data'
			});
		}

		this.form = new frappe.ui.FieldGroup({
			parent: this.$result,
			fields
		});

		this.form.make();
		this.form.set_values(this.data);
	}

	toggle_result_area() {
		this.$result.toggle(this.data.hub_item_code);
		this.$paging_area.toggle(this.data.length > 0);
		this.$no_result.toggle(this.data.length == 0);

		const show_more = (this.start + this.page_length) <= this.data.length;
		this.$paging_area.find('.btn-more')
			.toggle(show_more);
	}
};
