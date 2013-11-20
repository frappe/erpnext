// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Payment Made With Ageing"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: wn._("From Date"),
			fieldtype: "Date",
			default: wn.defaults.get_user_default("year_start_date"),
		},
		{
			fieldname:"to_date",
			label: wn._("To Date"),
			fieldtype: "Date",
			default: get_today()
		},
		{
			fieldname:"account",
			label: wn._("Supplier Account"),
			fieldtype: "Link",
			options: "Account",
			get_query: function() {
				return {
					query: "accounts.utils.get_account_list", 
					filters: {
						is_pl_account: "No",
						debit_or_credit: "Credit",
						company: wn.query_report.filters_by_name.company.get_value(),
						master_type: "Supplier"
					}
				}
			}
		},
		{
			fieldname:"company",
			label: wn._("Company"),
			fieldtype: "Link",
			options: "Company",
			default: wn.defaults.get_default("company")
		},
	]
}