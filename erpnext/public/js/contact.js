// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt
frappe.provide("erpnext.utils");

frappe.ui.form.on("Contact", {
	validate: function (frm) {
		erpnext.utils.format_mobile_pakistan_in_contact(frm);
		erpnext.utils.format_cnic(frm, "tax_cnic");
		erpnext.utils.format_mobile_pakistan(frm, "mobile_no");
		erpnext.utils.format_mobile_pakistan(frm, "mobile_no_2");
	},

	tax_cnic: function (frm) {
		erpnext.utils.format_cnic(frm, "tax_cnic");
	},

	mobile_no: function (frm) {
		erpnext.utils.format_mobile_pakistan(frm, "mobile_no");
	},
	mobile_no_2: function (frm) {
		erpnext.utils.format_mobile_pakistan(frm, "mobile_no_2");
	},
});

frappe.ui.form.on("Contact Phone", {
	phone: function(frm) {
		erpnext.utils.format_mobile_pakistan_in_contact(frm);
	},
	is_primary_mobile_no: function(frm) {
		erpnext.utils.format_mobile_pakistan_in_contact(frm);
	}
});
