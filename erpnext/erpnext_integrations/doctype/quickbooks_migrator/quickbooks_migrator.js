// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('QuickBooks Migrator', {
	connect: function(frm) {
		frappe.call({
			method: `${frm.python_path}.get_authorization_url`,
			callback: function (result) {
				window.open(result.message.url);
			}
		});
	},
	fetch_data: function(frm) {
		frappe.call({
			method: `${frm.python_path}.fetch_data`
		});
	},
	onload: function(frm){
		frm.python_path = "erpnext.erpnext_integrations.doctype.quickbooks_migrator.quickbooks_migrator";
		frm.is_authenticated = false;
		frappe.call({
			method: `${frm.python_path}.is_authenticated`,
			callback: function(authentication_result) {
				if (authentication_result.message) {
					frm.is_authenticated = true;
					frm.trigger("refresh");
				}
			}
		});
		frappe.realtime.on("quickbooks_progress_update", function (data) {
			switch (data.event) {
				case "fetch":
					frm.dashboard.show_progress("Sync", (data.count / data.total) * 100,
					`Fetching ${data.doctype}s (${data.count} / ${data.total})`);
					break;
				case "save":
					frm.dashboard.show_progress("Sync", (data.count / data.total) * 100,
					`Saving ${data.doctype}s (${data.count} / ${data.total})`);
					break;
			}
		});
		frappe.realtime.on("quickbooks_authenticated", function (data) {
			frm.is_authenticated = true;
			frm.trigger("refresh");
		});
	},
	refresh: function(frm){
		if (!frm.is_authenticated &&
			frm.fields_dict["client_id"].value &&
			frm.fields_dict["client_secret"].value &&
			frm.fields_dict["redirect_url"].value &&
			frm.fields_dict["scope"].value) {
			frm.add_custom_button("Connect to Quickbooks", function () {
				frm.trigger("connect");
			});
		}
		if (frm.is_authenticated) {
			frm.remove_custom_button("Connect to Quickbooks");

			// Show company settings
			frm.toggle_display("company_settings", 1);
			frm.set_df_property("company", "reqd", 1);
			frm.add_custom_button("Fetch Data", function () {
				frm.trigger("fetch_data");
			});

		}
	}
});
