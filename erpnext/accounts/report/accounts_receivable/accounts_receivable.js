// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.utils");

frappe.query_reports["Accounts Receivable"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "report_date",
			"label": __("Posting Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "finance_book",
			"label": __("Finance Book"),
			"fieldtype": "Link",
			"options": "Finance Book"
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			get_query: () => {
				var company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						'company': company
					}
				};
			}
		},
		{
			"fieldname":"party_type",
			"label": __("Party Type"),
			"fieldtype": "Autocomplete",
			options: get_party_type_options(),
			on_change: function() {
				frappe.query_report.set_filter_value('party', "");
				frappe.query_report.toggle_filter_display('customer_group', frappe.query_report.get_filter_value('party_type') !== "Customer");
			}
		},
		{
			"fieldname":"party",
			"label": __("Party"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				if (!frappe.query_report.filters) return;

				let party_type = frappe.query_report.get_filter_value('party_type');
				if (!party_type) return;

				return frappe.db.get_link_options(party_type, txt);
			},
		},
		{
			"fieldname": "party_account",
			"label": __("Receivable Account"),
			"fieldtype": "Link",
			"options": "Account",
			get_query: () => {
				var company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						'company': company,
						'account_type': 'Receivable',
						'is_group': 0
					}
				};
			}
		},
		{
			"fieldname": "ageing_based_on",
			"label": __("Ageing Based On"),
			"fieldtype": "Select",
			"options": 'Posting Date\nDue Date',
			"default": "Due Date"
		},
		{
			"fieldname": "range1",
			"label": __("Ageing Range 1"),
			"fieldtype": "Int",
			"default": "30",
			"reqd": 1
		},
		{
			"fieldname": "range2",
			"label": __("Ageing Range 2"),
			"fieldtype": "Int",
			"default": "60",
			"reqd": 1
		},
		{
			"fieldname": "range3",
			"label": __("Ageing Range 3"),
			"fieldtype": "Int",
			"default": "90",
			"reqd": 1
		},
		{
			"fieldname": "range4",
			"label": __("Ageing Range 4"),
			"fieldtype": "Int",
			"default": "120",
			"reqd": 1
		},
		{
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "MultiSelectList",
			"options": "Customer Group",
			get_data: function(txt) {
				return frappe.db.get_link_options('Customer Group', txt);
			}
		},
		{
			"fieldname": "payment_terms_template",
			"label": __("Payment Terms Template"),
			"fieldtype": "Link",
			"options": "Payment Terms Template"
		},
		{
			"fieldname": "sales_partner",
			"label": __("Sales Partner"),
			"fieldtype": "Link",
			"options": "Sales Partner"
		},
		{
			"fieldname": "sales_person",
			"label": __("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person"
		},
		{
			"fieldname": "territory",
			"label": __("Territory"),
			"fieldtype": "Link",
			"options": "Territory"
		},
		{
			"fieldname": "group_by_party",
			"label": __("Group By Customer"),
			"fieldtype": "Check"
		},
		{
			"fieldname": "based_on_payment_terms",
			"label": __("Based On Payment Terms"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "show_future_payments",
			"label": __("Show Future Payments"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "show_delivery_notes",
			"label": __("Show Linked Delivery Notes"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "show_sales_person",
			"label": __("Show Sales Person"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "show_remarks",
			"label": __("Show Remarks"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "for_revaluation_journals",
			"label": __("Revaluation Journals"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "ignore_accounts",
			"label": __("Group by Voucher"),
			"fieldtype": "Check",
		}


	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = value.bold();

		}
		return value;
	},

	onload: function(report) {
		report.page.add_inner_button(__("Accounts Receivable Summary"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Accounts Receivable Summary', {company: filters.company});
		});
	}
}

erpnext.utils.add_dimensions('Accounts Receivable', 9);


function get_party_type_options() {
	let options = [];
	frappe.db.get_list(
		"Party Type", {filters:{"account_type": "Receivable"}, fields:['name']}
	).then((res) => {
		res.forEach((party_type) => {
			options.push(party_type.name);
		});
	});
	return options;
}
