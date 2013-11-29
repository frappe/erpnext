// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Supplier-Wise Sales Analytics"] = {
	"filters": [
		{
			"fieldname":"supplier",
			"label": wn._("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": "80"
		},
		{
			"fieldname":"from_date",
			"label": wn._("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": wn.datetime.month_start()
		},
		{
			"fieldname":"to_date",
			"label": wn._("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": wn.datetime.month_end()
		},
	]
}