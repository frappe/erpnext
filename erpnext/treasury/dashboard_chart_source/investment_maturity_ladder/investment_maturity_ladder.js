frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Investment Maturity Ladder"] = {
	method: "erpnext.treasury.dashboard_chart_source.investment_maturity_ladder.investment_maturity_ladder.get",
	filters: [erpnext.treasury.get_company_filter()],
};
