frappe.query_reports["Subcontracting Inward Order Summary"] = {
	filters: [
		...erpnext.get_subcontracting_inward_report_filters(),
		{
			fieldname: "subcontracting_inward_order",
			label: __("Subcontracting Inward Order"),
			fieldtype: "Link",
			options: "Subcontracting Inward Order",
			get_query: () => ({ filters: { docstatus: 1 } }),
		},
	],
};
