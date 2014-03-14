// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Accounts Receivable"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": frappe._("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("company")
		},
		{
			"fieldname":"account",
			"label": frappe._("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				var company = frappe.query_report.filters_by_name.company.get_value();
				return {
					"query": "accounts.utils.get_account_list", 
					"filters": {
						"is_pl_account": "No",
						"root_type": "Asset",
						"company": company,
						"master_type": "Customer"
					}
				}
			}
		},
		{
			"fieldname":"report_date",
			"label": frappe._("Date"),
			"fieldtype": "Date",
			"default": get_today()
		},
		{
			"fieldname":"ageing_based_on",
			"label": frappe._("Ageing Based On"),
			"fieldtype": "Select",
			"options": 'Posting Date' + NEWLINE + 'Due Date',
			"default": "Posting Date"
		}
	]
}