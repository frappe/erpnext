// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

function fetch_gstins(report) {
	var company_gstins = report.get_filter('company_gstin');
	var company = report.get_filter_value('company');
	if (company) {
		frappe.call({
			method:'erpnext.regional.india.utils.get_gstins_for_company',
			async: false,
			args: {
				company: company
			},
			callback: function(r) {
				r.message.unshift("");
				company_gstins.df.options = r.message;
				company_gstins.refresh();
			}
		});
	} else {
		company_gstins.df.options = [""];
		company_gstins.refresh();
	}
}

frappe.query_reports["HSN-wise-summary of outward supplies"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company"),
			"on_change": fetch_gstins
		},
		{
			"fieldname":"gst_hsn_code",
			"label": __("HSN/SAC"),
			"fieldtype": "Link",
			"options": "GST HSN Code",
			"width": "80"
		},
		{
			"fieldname":"company_gstin",
			"label": __("Company GSTIN"),
			"fieldtype": "Select",
			"placeholder":"Company GSTIN",
			"options": [""],
			"width": "80"
		}
	],
	onload: (report) => {
		fetch_gstins(report);
	}
};
