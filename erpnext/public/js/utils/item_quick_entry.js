frappe.provide("frappe.ui.form");

frappe.ui.form.ItemQuickEntryForm = class ItemQuickEntryForm extends frappe.ui.form.QuickEntryForm {
	render_dialog() {
		super.render_dialog();
		const item_group = this.dialog.fields_dict.item_group;
		if (item_group) {
			item_group.get_query = () => ({ filters: { is_group: 0 } });
		}
	}
};
