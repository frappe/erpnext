// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('QuickBooks Connector', {
	fetch_data: function(frm) {
		frappe.call({
			method: "erpnext.erpnext_integrations.doctype.quickbooks_connector.quickbooks_connector.get_authorization_url",
			callback: function (url) {
				window.open(url.message);
			}
		});
	}
});
