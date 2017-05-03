// Copyright (c) 2016, ESS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sample Collection', {
	refresh: function(frm) {
		if(frappe.defaults.get_default("require_sample_collection")){
			frm.add_custom_button(__("View Procedures"), function() {
				frappe.route_options = {"sample": frm.doc.name}
				frappe.set_route("List", "Lab Test");
			});
		}
	}
});
