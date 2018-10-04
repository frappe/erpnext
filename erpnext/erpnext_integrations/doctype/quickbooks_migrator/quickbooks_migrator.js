// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('QuickBooks Migrator', {
	connect: function(frm) {
		window.open(frm.doc.authorization_url)
	},
	fetch_data: function(frm) {
		frappe.call({
			method: "erpnext.erpnext_integrations.doctype.quickbooks_migrator.quickbooks_migrator.fetch_data",
			freeze: true,
		});
	},
	onload: function(frm) {
		frappe.realtime.on("quickbooks_progress_update", function (data) {
			if (data.event == "fetch") {
				frm.dashboard.show_progress("Sync", (data.count / data.total) * 100, `Fetching ${data.doctype}s (${data.count} / ${data.total})`)
			}
			if (data.event == "save") {
				frm.dashboard.show_progress("Sync", (data.count / data.total) * 100, `Saving ${data.doctype}s (${data.count} / ${data.total})`)
			}
		});
	},
	refresh: function(frm){
		console.log("Refrehing")
		if (!frm.doc.access_token) {
			// Not connected yet
			// Need some details for connection though
			if (frm.doc.authorization_url) {
				frm.add_custom_button("Connect to Quickbooks", function () {
					frm.trigger("connect")
				});
			}
		}
		if (frm.doc.access_token) {
			// Already Connected
			// Don't Reconnect
			frm.remove_custom_button("Connect to Quickbooks")

			// Show company settings
			frm.toggle_display("company_settings", 1)
			frm.set_df_property("company", "reqd", 1)
			frm.add_custom_button("Fetch Data", function () {
				frm.trigger("fetch_data")
			});
		}
	}
});
