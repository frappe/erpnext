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
			"fieldname":"ageing_based_on",
			"label": __("Ageing Based On"),
			"fieldtype": "Select",
			"options": 'Posting Date\nDue Date',
			"default": "Posting Date"
		},
		{
			"fieldname":"report_date",
			"label": __("As on Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
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
			"fieldname":"range4",
			"label": __("Ageing Range 4"),
			"fieldtype": "Int",
			"default": "120",
			"reqd": 1
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			on_change: () => {
				var customer = frappe.query_report.get_filter_value('customer');
				if (customer) {
					frappe.db.get_value('Customer', customer, ["tax_id", "customer_name", "credit_limit", "payment_terms"], function(value) {
						frappe.query_report.set_filter_value('tax_id', value["tax_id"]);
						frappe.query_report.set_filter_value('customer_name', value["customer_name"]);
						frappe.query_report.set_filter_value('credit_limit', value["credit_limit"]);
						frappe.query_report.set_filter_value('payment_terms', value["payment_terms"]);
					});
				} else {
					frappe.query_report.set_filter_value('tax_id', "");
					frappe.query_report.set_filter_value('customer_name', "");
					frappe.query_report.set_filter_value('credit_limit', "");
					frappe.query_report.set_filter_value('payment_terms', "");
				}
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
			"fieldname":"territory",
			"label": __("Territory"),
			"fieldtype": "Link",
			"options": "Territory"
		},
		{
			"fieldname":"sales_partner",
			"label": __("Sales Partner"),
			"fieldtype": "Link",
			"options": "Sales Partner"
		},
		{
			"fieldname":"sales_person",
			"label": __("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person"
		},
		{
			"fieldname": "account",
			"label": __("Receivable Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					"doctype": "Account",
					"filters": {
						"company": company,
						"account_type": "Receivable",
						"is_group": 0
					}
				}
			}
		},
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center"
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname":"finance_book",
			"label": __("Finance Book"),
			"fieldtype": "Link",
			"options": "Finance Book"
		},
		{
			"fieldname":"group_by",
			"label": __("Group By Level 1"),
			"fieldtype": "Select",
			"options": "Ungrouped\nGroup by Customer\nGroup by Customer Group\nGroup by Territory\nGroup by Sales Person\nGroup by Cost Center\nGroup by Project",
			"default": "Ungrouped"
		},
		{
			"fieldname":"group_by_2",
			"label": __("Group By Level 2"),
			"fieldtype": "Select",
			"options": "Ungrouped\nGroup by Customer\nGroup by Customer Group\nGroup by Territory\nGroup by Sales Person\nGroup by Cost Center\nGroup by Project",
			"default": "Ungrouped"
		},
		{
			"fieldname":"from_age",
			"label": __("Show Invoices With Age Above"),
			"fieldtype": "Int"
		},
		{
			"fieldname":"based_on_payment_terms",
			"label": __("Based On Payment Terms"),
			"fieldtype": "Check",
		},
		{
			"fieldname":"show_pdc_in_print",
			"label": __("Show PDC in Print"),
			"fieldtype": "Check",
			on_change: function() { return false; }
		},
		{
			"fieldname":"mark_overdue_in_print",
			"label": __("Mark Overdue in Print"),
			"fieldtype": "Check",
			on_change: function() { return false; }
		},
		{
			"fieldname":"show_sales_person_in_print",
			"label": __("Show Sales Person in Print"),
			"fieldtype": "Check",
			"default": 1,
			on_change: function() { return false; }
		},
		{
			"fieldname":"tax_id",
			"label": __("NTN"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"customer_name",
			"label": __("Customer Name"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"payment_terms",
			"label": __("Payment Tems"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"credit_limit",
			"label": __("Credit Limit"),
			"fieldtype": "Currency",
			"hidden": 1
		}
	],

	onload: function(report) {
		report.page.add_inner_button(__("Accounts Receivable Summary"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Accounts Receivable Summary', {company: filters.company});
		});
		report.page.add_inner_button(__("Payment Reconciliation"), function() {
			var filters = report.get_values();
			frappe.set_route('Form', 'Payment Reconciliation', {
				company: filters.company,
				party_type: "Customer",
				party: filters.customer,
			});
		});
	},
	initial_depth: 1
}
