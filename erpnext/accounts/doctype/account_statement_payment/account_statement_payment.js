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
