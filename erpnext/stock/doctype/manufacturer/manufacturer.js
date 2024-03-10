// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

<<<<<<< HEAD
frappe.ui.form.on('Manufacturer', {
	refresh: function(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Manufacturer' };
=======
frappe.ui.form.on("Manufacturer", {
	refresh: function (frm) {
>>>>>>> ec74a5e566 (style: format js files)
		if (frm.doc.__islocal) {
			hide_field(["address_html", "contact_html"]);
			frappe.contacts.clear_address_and_contact(frm);
		} else {
			unhide_field(["address_html", "contact_html"]);
			frappe.contacts.render_address_and_contact(frm);
		}
	},
});
