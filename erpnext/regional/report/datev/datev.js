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
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1
		}
	],
	onload: function(query_report) {
		query_report.page.add_inner_button("Download DATEV Export", () => {
			const filters = JSON.stringify(query_report.get_values());
			window.open(`/api/method/erpnext.regional.report.datev.datev.download_datev_csv?filters=${filters}`);
		});
	}
};
