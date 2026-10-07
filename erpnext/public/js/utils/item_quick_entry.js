frappe.provide("frappe.ui.form");

frappe.ui.form.ItemQuickEntryForm = class ItemQuickEntryForm extends frappe.ui.form.QuickEntryForm {
	render_dialog() {
		super.render_dialog();
		this.set_query("item_group", () => ({ filters: { is_group: 0 } }));
	}
};
