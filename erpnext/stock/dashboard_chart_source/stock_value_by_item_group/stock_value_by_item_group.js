frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Stock Value by Item Group"] = {
	method: "erpnext.stock.dashboard_chart_source.stock_value_by_item_group.stock_value_by_item_group.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
	],
};
