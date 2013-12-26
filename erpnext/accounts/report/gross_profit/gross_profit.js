// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Gross Profit"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": wn._("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": wn.defaults.get_user_default("company")
		},
		{
			"fieldname":"from_date",
			"label": wn._("From Date"),
			"fieldtype": "Date",
			"default": wn.defaults.get_user_default("year_start_date")
		},
		{
			"fieldname":"to_date",
			"label": wn._("To Date"),
			"fieldtype": "Date",
			"default": wn.defaults.get_user_default("year_end_date")
		},
	]
}