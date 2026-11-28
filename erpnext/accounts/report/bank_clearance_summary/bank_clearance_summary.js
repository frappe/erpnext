// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Bank Clearance Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			width: "80",
		},
		{
			fieldname: "account",
			default: frappe.defaults.get_user_default("Company")
				? locals[":Company"][frappe.defaults.get_user_default("Company")]["default_bank_account"]
				: "",
			get_query: function () {
				return {
					query: "erpnext.controllers.queries.get_account_list",
					filters: [
						["Account", "account_type", "in", "Bank, Cash"],
						["Account", "is_group", "=", 0],
					],
				};
			},
		},
	],
};
