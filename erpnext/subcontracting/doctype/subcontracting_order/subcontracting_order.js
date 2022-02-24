// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subcontracting Order', {
	setup: function (frm) {
		frm.set_query('purchase_order', () => {
			return {
				filters: {
					docstatus: 1,
					is_subcontracted: 'Yes'
				}
			};
		});

		frm.set_query("item_code", "service_items", () => {
			return {
				filters: {
					is_stock_item: 0
				}
			};
		});
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1) {
			cur_frm.add_custom_button(__('Subcontracting Receipt'), make_subcontracting_receipt, __('Create'));
			cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
	},
});

let make_subcontracting_receipt = () => {
	frappe.model.open_mapped_doc({
		method: "erpnext.buying.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt",
		frm: cur_frm,
		freeze_message: __("Creating Subcontracting Receipt ...")
	})
}