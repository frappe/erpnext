// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Account Statement Payment', {
	// refresh: function(frm) {

	// }

	// onload: function(frm) {
	// 	frappe.call({
	// 		method: "add_products_detail",
	// 		doc: frm.doc,
	// 		callback: function(r) {
	// 		}
	// 	});
	// }, 
	refresh: function (frm) {
		frm.events.make_custom_buttons(frm);
	},

	make_custom_buttons: function (frm) {
		frm.add_custom_button(__("Excel"),
			() => frm.events.export_to_excel(frm), __('Create'));

		frm.page.set_inner_btn_group_as_primary(__('Create'));
	},

	export_to_excel: function (frm) {
		frappe.call({
			method: "export_to_excel",
			doc: frm.doc,
		});
	},

	calculate: function(frm) {
		frappe.call({
			method: "calculate_discount",
			doc: frm.doc,
			callback: function(r) {
				frm.set_value("total_sale", r.message.total_sale);
				frm.set_value("total_discount", r.message.total_discount);
			}
		});
	}
});
