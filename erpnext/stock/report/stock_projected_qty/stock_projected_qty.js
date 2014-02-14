// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Stock Projected Qty"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": frappe._("Company"),
			"fieldtype": "Link",
			"options": "Company"
		},
		{
			"fieldname":"warehouse",
			"label": frappe._("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname":"item_code",
			"label": frappe._("Item"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname":"brand",
			"label": frappe._("Brand"),
			"fieldtype": "Link",
			"options": "Brand"
		}
	]
}