// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Accounts Receivable"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			on_change: () => {
				var customer = frappe.query_report_filters_by_name.customer.get_value();
				frappe.db.get_value('Customer', customer, "tax_id", function(value) {
					frappe.query_report_filters_by_name.tax_id.set_value(value["tax_id"]);
				});
			}
		},
		{
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group"
		},
		{
			"fieldname":"payment_terms_template",
			"label": __("Payment Terms Template"),
			"fieldtype": "Link",
			"options": "Payment Terms Template"
		},
		{
			"fieldtype": "Break",
		},
		{
			"fieldname":"report_date",
			"label": __("As on Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"ageing_based_on",
			"label": __("Ageing Based On"),
			"fieldtype": "Select",
			"options": 'Posting Date\nDue Date',
			"default": "Posting Date"
		},
		{
			"fieldname":"range1",
			"label": __("Ageing Range 1"),
			"fieldtype": "Int",
			"default": "30",
			"reqd": 1
		},
		{
			"fieldname":"range2",
			"label": __("Ageing Range 2"),
			"fieldtype": "Int",
			"default": "60",
			"reqd": 1
		},
		{
			"fieldname":"range3",
			"label": __("Ageing Range 3"),
			"fieldtype": "Int",
			"default": "90",
			"reqd": 1
		},
		{
			"fieldname":"show_pdc_in_print",
			"label": __("Show PDC in Print"),
			"fieldtype": "Check",
		},
		{
			"fieldname":"tax_id",
			"label": __("Tax Id"),
			"fieldtype": "Data",
			"hidden": 1
		}
	],

	onload: function(report) {
		report.page.add_inner_button(__("Accounts Receivable Summary"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Accounts Receivable Summary', {company: filters.company});
		});
	}
}
