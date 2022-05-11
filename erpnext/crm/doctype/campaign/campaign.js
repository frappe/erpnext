// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Campaign', {
	refresh: function(frm) {
		erpnext.toggle_naming_series();

		if (frm.is_new()) {
			frm.toggle_display("naming_series", frappe.boot.sysdefaults.campaign_naming_by=="Naming Series");
		} else {
			cur_frm.add_custom_button(__("View Leads"), function() {
				frappe.route_options = {"source": "Campaign", "campaign_name": frm.doc.name};
				frappe.set_route("List", "Lead");
			}, "fa fa-list", true);
		}
	}
});
