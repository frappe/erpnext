// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shareholder', {
	refresh: function(frm) {
		frm.add_custom_button(__("Share Balance"), function(){
			frappe.route_options = {
				"shareholder": frm.doc.name,
			};
			frappe.set_route("query-report", "Share Balance");
		});
		frm.add_custom_button(__("Share Ledger"), function(){
			frappe.route_options = {
				"shareholder": frm.doc.name,
			};
			frappe.set_route("query-report", "Share Ledger");
		});
	}
});
