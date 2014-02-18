// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/purchase_trends_filters.js");

frappe.query_reports["Purchase Invoice Trends"] = {
	filters: get_filters()
 }