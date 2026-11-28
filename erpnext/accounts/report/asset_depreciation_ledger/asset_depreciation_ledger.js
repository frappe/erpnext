// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Asset Depreciation Ledger"] = {
	filters: [
		{
			fieldname: "from_date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "cost_center",
			get_data: function (txt) {
				let company = frappe.query_report.get_filter_value("company");
				return erpnext.utils.get_link_options("Cost Center", txt, company ? { company } : {});
			},
		},
	],
};
