// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include "erpnext/accounts/report/sales_register/sales_register.js" %}

frappe.query_reports["Electronic Invoice Register"] = frappe.query_reports["Sales Register"]

frappe.query_reports["Electronic Invoice Register"]["onload"] = function(reportview) {
	reportview.page.add_inner_button(__("Export for SDI"), function() {
		
	})
}
