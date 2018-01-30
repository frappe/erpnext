// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Asset Report"] = {
	"filters": [
		{
			"fieldname":"asset_category",
			"label": __("Asset Category"),
			"fieldtype": "Link",
			"options": "Asset Category"
		},
	]
}
