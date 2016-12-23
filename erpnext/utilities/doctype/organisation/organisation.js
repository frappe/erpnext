// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Organisation', {
	refresh: function(frm) {
		frm.toggle_display(['address_html','contact_html'], !frm.doc.__islocal);

		if(!frm.doc.__islocal) {
			erpnext.utils.render_address_and_contact(frm);
		} else {
			erpnext.utils.clear_address_and_contact(frm);
		}
	}
});
