// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.ui.form.on('Amazon MWS Settings', {
	refresh: function (frm) {
		let app_link = "<a href='https://github.com/frappe/ecommerce_integrations' target='_blank'>Ecommerce Integrations</a>"
		frm.dashboard.add_comment(__("Amazon MWS Integration will be removed from ERPNext in Version 14. Please install {0} app to continue using it.", [app_link]), "yellow", true);
	}
});
