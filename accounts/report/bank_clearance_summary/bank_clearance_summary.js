// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Bank Clearance Summary"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": wn._("From Date"),
			"fieldtype": "Date",
			"default": wn.defaults.get_user_default("year_start_date"),
			"width": "80"
		},
		{
			"fieldname":"to_date",
			"label": wn._("To Date"),
			"fieldtype": "Date",
			"default": get_today()
		},
		{
			"fieldname":"account",
			"label": wn._("Bank Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				return {
					"query": "accounts.utils.get_account_list", 
					"filters": {
						"is_pl_account": "No",
						"account_type": "Bank or Cash"
					}
				}
			}
		},
	]
}