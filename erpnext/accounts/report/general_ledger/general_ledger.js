// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["General Ledger"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "account",
			label: __("Account"),
			fieldtype: "MultiSelectList",
			options: "Account",
			get_data: function (txt) {
				return frappe.db.get_link_options("Account", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "voucher_no",
			label: __("Voucher No"),
			fieldtype: "Data",
			on_change: function () {
<<<<<<< HEAD
				frappe.query_report.set_filter_value("categorize_by", "Categorize by Voucher (Consolidated)");
=======
				frappe.query_report.set_filter_value("group_by", "Group by Voucher (Consolidated)");
>>>>>>> 7c4cf3e834 (Favicon.svg)
			},
		},
		{
			fieldname: "against_voucher_no",
			label: __("Against Voucher No"),
			fieldtype: "Data",
		},
		{
			fieldtype: "Break",
		},
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Autocomplete",
			options: Object.keys(frappe.boot.party_account_types),
			on_change: function () {
<<<<<<< HEAD
				frappe.query_report.set_filter_value("party", []);
=======
				frappe.query_report.set_filter_value("party", "");
>>>>>>> 7c4cf3e834 (Favicon.svg)
			},
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "MultiSelectList",
<<<<<<< HEAD
			options: "party_type",
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
			get_data: function (txt) {
				if (!frappe.query_report.filters) return;

				let party_type = frappe.query_report.get_filter_value("party_type");
				if (!party_type) return;

				return frappe.db.get_link_options(party_type, txt);
			},
			on_change: function () {
				var party_type = frappe.query_report.get_filter_value("party_type");
				var parties = frappe.query_report.get_filter_value("party");

				if (!party_type || parties.length === 0 || parties.length > 1) {
					frappe.query_report.set_filter_value("party_name", "");
					frappe.query_report.set_filter_value("tax_id", "");
					return;
				} else {
					var party = parties[0];
					var fieldname = erpnext.utils.get_party_name(party_type) || "name";
					frappe.db.get_value(party_type, party, fieldname, function (value) {
						frappe.query_report.set_filter_value("party_name", value[fieldname]);
					});

					if (party_type === "Customer" || party_type === "Supplier") {
						frappe.db.get_value(party_type, party, "tax_id", function (value) {
							frappe.query_report.set_filter_value("tax_id", value["tax_id"]);
						});
					}
				}
			},
		},
		{
			fieldname: "party_name",
			label: __("Party Name"),
			fieldtype: "Data",
			hidden: 1,
		},
		{
<<<<<<< HEAD
			fieldname: "categorize_by",
			label: __("Categorize by"),
=======
			fieldname: "group_by",
			label: __("Group by"),
>>>>>>> 7c4cf3e834 (Favicon.svg)
			fieldtype: "Select",
			options: [
				"",
				{
<<<<<<< HEAD
					label: __("Categorize by Voucher"),
					value: "Categorize by Voucher",
				},
				{
					label: __("Categorize by Voucher (Consolidated)"),
					value: "Categorize by Voucher (Consolidated)",
				},
				{
					label: __("Categorize by Account"),
					value: "Categorize by Account",
				},
				{
					label: __("Categorize by Party"),
					value: "Categorize by Party",
				},
			],
			default: "Categorize by Voucher (Consolidated)",
=======
					label: __("Group by Voucher"),
					value: "Group by Voucher",
				},
				{
					label: __("Group by Voucher (Consolidated)"),
					value: "Group by Voucher (Consolidated)",
				},
				{
					label: __("Group by Account"),
					value: "Group by Account",
				},
				{
					label: __("Group by Party"),
					value: "Group by Party",
				},
			],
			default: "Group by Voucher (Consolidated)",
>>>>>>> 7c4cf3e834 (Favicon.svg)
		},
		{
			fieldname: "tax_id",
			label: __("Tax Id"),
			fieldtype: "Data",
			hidden: 1,
		},
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
<<<<<<< HEAD
			options: "Cost Center",
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "MultiSelectList",
<<<<<<< HEAD
			options: "Project",
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
			get_data: function (txt) {
				return frappe.db.get_link_options("Project", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "include_dimensions",
			label: __("Consider Accounting Dimensions"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_opening_entries",
			label: __("Show Opening Entries"),
			fieldtype: "Check",
		},
		{
			fieldname: "include_default_book_entries",
			label: __("Include Default FB Entries"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_cancelled_entries",
			label: __("Show Cancelled Entries"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_net_values_in_party_account",
			label: __("Show Net Values in Party Account"),
			fieldtype: "Check",
		},
		{
<<<<<<< HEAD
			fieldname: "show_amount_in_company_currency",
			label: __("Show Credit / Debit in Company Currency"),
			fieldtype: "Check",
		},
		{
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
			fieldname: "add_values_in_transaction_currency",
			label: __("Add Columns in Transaction Currency"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_remarks",
			label: __("Show Remarks"),
			fieldtype: "Check",
		},
		{
			fieldname: "ignore_err",
<<<<<<< HEAD
			label: __("Ignore Exchange Rate Revaluation and Gain / Loss Journals"),
=======
			label: __("Ignore Exchange Rate Revaluation Journals"),
>>>>>>> 7c4cf3e834 (Favicon.svg)
			fieldtype: "Check",
		},
		{
			fieldname: "ignore_cr_dr_notes",
			label: __("Ignore System Generated Credit / Debit Notes"),
			fieldtype: "Check",
		},
	],
<<<<<<< HEAD
	collapsible_filters: true,
	seperate_check_filters: true,
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
};

erpnext.utils.add_dimensions("General Ledger", 15);
