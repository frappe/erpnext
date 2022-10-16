// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["TDS Certificate"] = {
	"filters": [
		{
			"fieldname": "party_type",
			"label": __("Party Type"),
			"fieldtype": "Select",
			"options": "\nSupplier\nCustomer",
			"reqd": 1,
			"on_change":function(query_report){
				var party_type = query_report.get_filter_value('party_type')
				if (party_type == 'Customer'){
					query_report.get_filter('customer').toggle(party_type == 'Customer' ? 1:0)
					query_report.get_filter('supplier').toggle(party_type == 'Customer' ? 0:1)
				}
				if (party_type == 'Supplier'){
					query_report.get_filter('supplier').toggle(party_type == 'Supplier' ? 1:0)
					query_report.get_filter('customer').toggle(party_type == 'Supplier' ? 0:1)
				}
			}
		},
		{
			"fieldname": "customer",
			"label": __("Customer Name"),
			"fieldtype": "Link",
			"options": "Customer",
			"hidden": 1,
			"on_change": function(query_report) {
				var customer = query_report.get_filter_value('customer')
				if (!customer) {
					return;
				}
				frappe.model.with_doc("Customer", customer, function(r) {
					var customer = frappe.model.get_doc("Customer", customer);
					query_report.set_filter_value("vendor_tpn_no", customer.tax_id);
					query_report.refresh("vendor_tpn_no");
				});
			}
		},
		{
			"fieldname": "supplier",
			"label": __("Supplier Name"),
			"fieldtype": "Link",
			"options": "Supplier",
			"hidden": 1,
			"on_change": function(query_report) {
				var supplier = query_report.get_filter_value('supplier');
				if (!supplier) {
					return;
				}
				frappe.model.with_doc("Supplier", supplier, function(r) {
					var supplier = frappe.model.get_doc("Supplier", supplier);
					query_report.set_filter_value("vendor_tpn_no", supplier.vendor_tpn_no);
					query_report.refresh("vendor_tpn_no");
				});
			}
		},
		{
			"fieldname": "vendor_tpn_no",
			"label": __("Vendor TPN Number"),
			"fieldtype": "Data",
			"read_only": 1
		},
		{
			"fieldname": "currency",
			"label" : __("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"reqd": 1,
		},
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1,
			on_change: function (query_report) {
				var fiscal_year = query_report.get_values().fiscal_year;
				if (!fiscal_year) {
					return;
				}
				frappe.model.with_doc("Fiscal Year", fiscal_year, function (r) {
					var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
					frappe.query_report.set_filter_value({
						from_date: fy.year_start_date,
						to_date: fy.year_end_date,
					});
				});
			},
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date"),
		}
	]
}
