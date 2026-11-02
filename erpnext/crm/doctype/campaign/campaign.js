// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Campaign", {
	refresh: function (frm) {
		erpnext.toggle_naming_series(frm);

		if (frm.is_new()) {
			frm.toggle_display(
				"naming_series",
				frappe.boot.sysdefaults.campaign_naming_by == "Naming Series"
			);
		} else {
			frm.add_custom_button(
				__("View Leads"),
				function () {
					// leads link to the UTM Campaign mirror, named after campaign_name
					frappe
						.call("erpnext.crm.doctype.campaign.campaign.get_utm_campaign", {
							campaign: frm.doc.name,
						})
						.then(({ message }) => {
							frappe.route_options = { utm_campaign: message };
							frappe.set_route("List", "Lead");
						});
				},
				null,
				true
			);
		}
	},
});
