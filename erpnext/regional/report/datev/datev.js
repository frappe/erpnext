frappe.query_reports["DATEV"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1
		}
	],
	onload: function(query_report) {
		query_report.export_report = function() {
			const filters = JSON.stringify(query_report.get_values());
			window.open(`/api/method/erpnext.regional.report.datev.datev.download_datev_csv?filters=${filters}`);
		};
	}
};
