// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["TDS Payable Monthly"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_default('company')
		},
		{
			"fieldname":"supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"get_query": function() {
				return {
					"filters": {
						"tax_withholding_category": ["!=", ""],
					}
				}
			},
			on_change: function() {
				frappe.query_report.set_filter_value("purchase_invoice", "");
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname":"purchase_invoice",
			"label": __("Purchase Invoice"),
			"fieldtype": "Link",
			"options": "Purchase Invoice",
			"get_query": function() {
				return {
					"filters": {
						"name": ["in", frappe.query_report.invoices]
					}
				}
			},
			on_change: function() {
				let supplier = frappe.query_report.get_filter_value('supplier');
				if(!supplier) return; // return if no supplier selected

				// filter invoices based on selected supplier
				let invoices = [];
				frappe.query_report.invoice_data.map(d => {
					if(d.supplier==supplier)
						invoices.push(d.name)
				});
				frappe.query_report.invoices = invoices;
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "60px"
		}
	],

	onload: function(report) {
		// fetch all tds applied invoices
		frappe.call({
			"method": "erpnext.accounts.report.tds_payable_monthly.tds_payable_monthly.get_tds_invoices",
			callback: function(r) {
				let invoices = [];
				r.message.map(d => {
					invoices.push(d.name);
				});

				report["invoice_data"] = r.message;
				report["invoices"] = invoices;
			}
		});
	}
}
