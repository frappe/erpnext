// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Employee Leave Balance"] = {
	"filters": [
		{
			"fieldname":"fiscal_year",
			"label": wn._("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": wn.defaults.get_user_default("fiscal_year")
		},
		{
			"fieldname":"company",
			"label": wn._("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": wn.defaults.get_user_default("company")
		}
	]
}