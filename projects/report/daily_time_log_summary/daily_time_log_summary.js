// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Daily Time Log Summary"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": wn._("From Date"),
			"fieldtype": "Date",
			"default": wn.datetime.get_today()
		},
		{
			"fieldname":"to_date",
			"label": wn._("To Date"),
			"fieldtype": "Date",
			"default": wn.datetime.get_today()
		},
	]
}