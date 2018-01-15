// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shareholder', {
	refresh: function(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Shareholder' };

		frm.toggle_display(['contact_html'], !frm.doc.__islocal);

		if (frm.doc.__islocal) {
			hide_field(['contact_html']);
			frappe.contacts.clear_address_and_contact(frm);
		}
		else {
			if (frm.doc.is_company){
				hide_field(['company']);
			} else {
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
				unhide_field(['contact_html']);
				frappe.contacts.render_address_and_contact(frm);
			}
		}
	}
});
