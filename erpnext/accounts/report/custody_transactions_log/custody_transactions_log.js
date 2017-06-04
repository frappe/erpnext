// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Custody Transactions Log"] = {
	"filters": [
		{
			"fieldname":"fixed_asset",
			"label": __("Fixed Asset"),
			"fieldtype": "Link",
			"options": "Asset"
		}
	]
}
