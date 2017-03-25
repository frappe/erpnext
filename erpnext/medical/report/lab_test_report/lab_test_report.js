// Copyright (c) 2016, ESS
// License: See license.txt

frappe.query_reports["Lab Test Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": get_today(),
			"width": "80"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": get_today()
		},
		{
			"fieldname":"patient",
			"label": __("Patient"),
			"fieldtype": "Link",
			"options": "Patient"
		},
		{
			"fieldname":"department",
			"label": __("Medical Department"),
			"fieldtype": "Link",
			"options": "Medical Department"
		}
	]
}
