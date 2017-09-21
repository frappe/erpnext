// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Daily Movements"] = {
	"filters": [
        {
			"fieldname":"target_date",
			"label": __("Target Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"mode_of_payment",
			"label": __("Medio de Pago"),
			"fieldtype": "Link",
			"options": "Mode of Payment"
		}
	]
}
