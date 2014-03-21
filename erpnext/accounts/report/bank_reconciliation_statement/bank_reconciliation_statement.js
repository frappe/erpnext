// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Bank Reconciliation Statement"] = {
	"filters": [
		{
			"fieldname":"account",
			"label": frappe._("Bank Account"),
			"fieldtype": "Link",
			"options": "Account",
			"reqd": 1,
			"get_query": function() {
				return {
					"query": "accounts.utils.get_account_list", 
					"filters": [
						['Account', 'account_type', 'in', 'Bank, Cash'],
						['Account', 'group_or_ledger', '=', 'Ledger'],
					]
				}
			}
		},
		{
			"fieldname":"report_date",
			"label": frappe._("Date"),
			"fieldtype": "Date",
			"default": get_today(),
			"reqd": 1
		},
	]
}