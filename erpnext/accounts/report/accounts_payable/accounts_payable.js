// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Accounts Payable"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"finance_book",
			"label": __("Finance Book"),
			"fieldtype": "Link",
			"options": "Finance Book"
		},
		{
			"fieldname":"supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			on_change: () => {
				var supplier = frappe.query_report.get_filter_value('supplier');
				frappe.db.get_value('Supplier', supplier, "tax_id", function(value) {
					frappe.query_report.set_filter_value('tax_id', value["tax_id"]);
				});
			}
		},
		{
			"fieldname":"supplier_group",
			"label": __("Supplier Group"),
			"fieldtype": "Link",
			"options": "Supplier Group"
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
			"options": 'Posting Date\nDue Date\nSupplier Invoice Date',
			"default": "Posting Date"
		},
		{
			"fieldtype": "Break",
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
			"fieldname":"tax_id",
			"label": __("Tax Id"),
			"fieldtype": "Data",
			"hidden": 1
		}
	],
	onload: function(report) {
		report.page.add_inner_button(__("Accounts Payable Summary"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Accounts Payable Summary', {company: filters.company});
		});
	}
}
