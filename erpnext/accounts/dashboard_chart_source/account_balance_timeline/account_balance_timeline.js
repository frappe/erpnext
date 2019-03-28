frappe.dashboard_chart_sources["Account Balance Timeline"] = {
	method_path: "erpnext.accounts.dashboard_chart_source.account_balance_timeline.account_balance_timeline.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "account",
			label: __("Account"),
			fieldtype: "Link",
			options: "Account",
			reqd: 1
		},
		{
			fieldname: "timespan",
			label: __("Period"),
			fieldtype: "Select",
			options: [
				{value: "Last Year", label: __("Last Year")},
				{value: "Last Quarter", label: __("Last Quarter")},
				{value: "Last Month", label: __("Last Month")},
				{value: "Last Week", label: __("Last Week")}
			],
			reqd: 1
		},
		{
			fieldname: "timegrain",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: [
				{value: "Quarterly", label: __("Quarterly")},
				{value: "Monthly", label: __("Monthly")},
				{value: "Weekly", label: __("Weekly")},
				{value: "Daily", label: __("Daily")}
			],
			reqd: 1
		},
	],
	is_time_series: true
};