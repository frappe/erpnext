frappe.provide('frappe.dashboards.chart_sources');

frappe.dashboards.chart_sources["Account Balance Timeline"] = {
	method: "erpnext.accounts.dashboard_chart_source.account_balance_timeline.account_balance_timeline.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "account",
			label: __("Account"),
			fieldtype: "Link",
			options: "Account",
		},
		{
			fieldname: "accumulated_values",
			label: __("Accumulated Values"),
			fieldtype: "Check",
		},
		{
			fieldname: "account_type",
			label: __("Account Type"),
			fieldtype: "Data",
		},
		{
			fieldname: "root_type",
			label: __("Root Type"),
			fieldtype: 'MultiSelect',
			options: [
				'Asset',
				'Liability',
				'Equity',
				'Income',
				'Expense',
			]
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["", "Account", "Root Type"],
		},
		{
			fieldname: "add_pnl_dataset",
			label: __("Add Profit and Loss Dataset"),
			fieldtype: "Check",
			depends_on: "eval:doc.group_by == 'Root Type'",
		},
	]
};
