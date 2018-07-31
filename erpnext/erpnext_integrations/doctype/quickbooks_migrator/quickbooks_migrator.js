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
	fetch_accounts: function(frm) {
		frappe.call({
			method: `${frm.python_path}.fetch_accounts`
		});
	},
	delete_default_accounts: function(frm) {
		frappe.call({
			method: `${frm.python_path}.delete_default_accounts`
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
		frm.are_accounts_synced = false;
		frappe.call({
			method: `${frm.python_path}.is_authenticated`,
			callback: function(authentication_result) {
				if (authentication_result.message) {
					frm.is_authenticated = true;
					frappe.call({
						method: `${frm.python_path}.are_accounts_synced`,
						callback: function(account_sync_result) {
							frm.are_accounts_synced = account_sync_result.message;
							frm.trigger("refresh");	
						}
					});
				}
			}
		});
		frappe.realtime.on("quickbooks_progress_update", function (data) {
			switch (data.event) {
			   case "fetch":
				   frappe.show_progress("Fetching " + data.doctype + "s", data.count, data.total);
				   break;
			   case "save":
				   frappe.show_progress("Saving " + data.doctype + "s", data.count, data.total);
				   break;
			   case "finish":
				   frappe.hide_progress();
				   break;
			   case "message":
				   frappe.hide_msgprint();
				   frappe.show_alert(data.message);
				   break;
		   }
	    });
		frappe.realtime.on("quickbooks_authenticated", function (data) {
			frm.is_authenticated = true;
			frm.trigger("refresh");
		});
		frappe.realtime.on("quickbooks_accounts_synced", function (data) {
			frm.are_accounts_synced = true;
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
			frm.add_custom_button("Fetch Accounts", function () {
				frm.trigger("fetch_accounts");
			});
			if (frm.are_accounts_synced){
				frm.add_custom_button("Delete Default Accounts", function () {
					frm.trigger("delete_default_accounts");
				});
				frm.add_custom_button("Fetch Data", function () {
					frm.trigger("fetch_data");
				});
			}
		}
	}
});
