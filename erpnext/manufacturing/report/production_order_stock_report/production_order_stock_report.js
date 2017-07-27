// Copyright (c) 2016, Velometro Mobility Inc and contributors
// For license information, please see license.txt

frappe.query_reports["Production Order Stock Report"] = {
	"filters": [
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		}
	]
}
