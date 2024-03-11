// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Homepage", {
	refresh: function (frm) {
		frm.add_custom_button(__("Set Meta Tags"), () => {
			frappe.utils.set_meta_tag("home");
		});
		frm.add_custom_button(__("Customize Homepage Sections"), () => {
			frappe.set_route("List", "Homepage Section", "List");
		});
	},
});
