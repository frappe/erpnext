// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Warehouse-Wise Stock Balance"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": wn._("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": sys_defaults.year_start_date,
		},
		{
			"fieldname":"to_date",
			"label": wn._("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": wn.datetime.get_today()
		}
	]
}