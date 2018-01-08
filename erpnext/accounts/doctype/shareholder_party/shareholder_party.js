// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shareholder Party', {
	refresh: (frm) => {
		if (frm.doc.folio_no){
			frm.add_custom_button(__("Share Balance"), function(){
				frappe.route_options = {
					"shareholder_party": frm.doc.name,
				};
				frappe.set_route("query-report", "Share Balance");
			});
			frm.add_custom_button(__("Share Ledger"), function(){
				frappe.route_options = {
					"shareholder_party": frm.doc.name,
				};
				frappe.set_route("query-report", "Share Ledger");
			});
		}
	}
});
