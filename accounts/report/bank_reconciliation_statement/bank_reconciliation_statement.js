// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Bank Reconciliation Statement"] = {
	"filters": [
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
		{
			"fieldname":"report_date",
			"label": wn._("Date"),
			"fieldtype": "Date",
			"default": get_today()
		},
	]
}