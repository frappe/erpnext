frappe.query_reports["Subcontracting Inward Order Summary"] = {
	filters: [
		...erpnext.get_subcontracting_inward_report_filters(),
		{
			fieldname: "subcontracting_inward_order",
			label: __("Subcontracting Inward Order"),
			fieldtype: "Link",
			options: "Subcontracting Inward Order",
			get_query: () => {
				const report = frappe.query_report;
				const filters = {
					docstatus: 1,
					company: report.get_filter_value("company"),
					transaction_date: [
						"between",
						[report.get_filter_value("from_date"), report.get_filter_value("to_date")],
					],
				};
				if (report.get_filter_value("customer")) {
					filters.customer = report.get_filter_value("customer");
				}

				return { filters };
			},
		},
	],
};
