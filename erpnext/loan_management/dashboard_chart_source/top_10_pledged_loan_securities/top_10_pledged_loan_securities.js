frappe.provide('frappe.dashboards.chart_sources');

frappe.dashboards.chart_sources["Top 10 Pledged Loan Securities"] = {
	method: "erpnext.loan_management.dashboard_chart_source.top_10_pledged_loan_securities.top_10_pledged_loan_securities.get_data",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		}
	]
};
