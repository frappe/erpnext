// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Batch-Wise Balance History"] = {
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