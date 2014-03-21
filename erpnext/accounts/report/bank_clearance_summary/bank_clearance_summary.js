// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Bank Clearance Summary"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": frappe._("From Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
			"width": "80"
		},
		{
			"fieldname":"to_date",
			"label": frappe._("To Date"),
			"fieldtype": "Date",
			"default": get_today()
		},
		{
			"fieldname":"account",
			"label": frappe._("Bank Account"),
			"fieldtype": "Link",
			"options": "Account",
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
	]
}