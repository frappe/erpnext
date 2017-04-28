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
			"fieldname":"lab_test_type",
			"label": __("Service Type"),
			"fieldtype": "Link",
			"options": "Service Type"
		}
	]
}
