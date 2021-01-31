// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt
frappe.provide("erpnext.utils");

frappe.ui.form.on("Contact", {
	refresh: function(frm) {
		erpnext.utils.format_mobile_pakistan_in_contact(frm);
	}
});

frappe.ui.form.on("Contact Phone", {
	phone: function(frm) {
		erpnext.utils.format_mobile_pakistan_in_contact(frm);
	},
	is_primary_mobile_no: function(frm) {
		erpnext.utils.format_mobile_pakistan_in_contact(frm);
	}
});
