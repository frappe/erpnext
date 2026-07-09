// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Accounts Payable"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "report_date",
			label: __("Posting Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
			options: "Cost Center",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "MultiSelectList",
			options: "Project",
			get_data: function (txt) {
				return frappe.db.get_link_options("Project", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "party_account",
			label: __("Payable Account"),
			fieldtype: "Link",
			options: "Account",
			get_query: () => {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company,
						account_type: "Payable",
						is_group: 0,
					},
				};
			},
		},
		{
			fieldname: "ageing_based_on",
			label: __("Ageing Based On"),
			fieldtype: "Select",
			options: "Posting Date\nDue Date\nSupplier Invoice Date",
			default: "Due Date",
		},
		{
			fieldname: "calculate_ageing_with",
			label: __("Calculate Ageing With"),
			fieldtype: "Select",
			options: "Report Date\nToday Date",
			default: "Report Date",
		},
		{
			fieldname: "range",
			label: __("Ageing Range"),
			fieldtype: "Data",
			default: "30, 60, 90, 120",
		},
		{
			fieldname: "payment_terms_template",
			label: __("Payment Terms Template"),
			fieldtype: "Link",
			options: "Payment Terms Template",
		},
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Autocomplete",
			options: get_party_type_options(),
			on_change: function () {
				frappe.query_report.set_filter_value("party", "");
				frappe.query_report.toggle_filter_display(
					"supplier_group",
					frappe.query_report.get_filter_value("party_type") !== "Supplier"
				);
			},
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "MultiSelectList",
			options: "party_type",
			get_data: function (txt) {
				if (!frappe.query_report.filters) return;

				let party_type = frappe.query_report.get_filter_value("party_type");
				if (!party_type) return;

				return frappe.db.get_link_options(party_type, txt);
			},
		},
		{
			fieldname: "supplier_group",
			label: __("Supplier Group"),
			fieldtype: "Link",
			options: "Supplier Group",
			hidden: 1,
		},
		{
			fieldname: "group_by_party",
			label: __("Group By Supplier"),
			fieldtype: "Check",
		},
		{
			fieldname: "based_on_payment_terms",
			label: __("Based On Payment Terms"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_remarks",
			label: __("Show Remarks"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_future_payments",
			label: __("Show Future Payments"),
			fieldtype: "Check",
		},
		{
			fieldname: "in_party_currency",
			label: __("In Party Currency"),
			fieldtype: "Check",
		},
		{
			fieldname: "for_revaluation_journals",
			label: __("Revaluation Journals"),
			fieldtype: "Check",
		},
		{
			fieldname: "ignore_accounts",
			label: __("Group by Voucher"),
			fieldtype: "Check",
		},
		{
			fieldname: "handle_employee_advances",
			label: __("Handle Employee Advances"),
			fieldtype: "Check",
		},
	],
	collapsible_filters: true,
	separate_check_filters: true,

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = value.bold();
		}
		return value;
	},

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
			events: {
				onCheckRow: () => erpnext.accounts.toggle_create_pe_primary_action(frappe.query_report),
			},
		});
	},

	after_refresh: function (report) {
		report.datatable?.rowmanager?.checkAll(false);
		report.page.clear_primary_action();
	},

	onload: function (report) {
		report.page.add_inner_button(__("Accounts Payable Summary"), function () {
			var filters = report.get_values();
			frappe.set_route("query-report", "Accounts Payable Summary", { company: filters.company });
		});

		if (frappe.boot.sysdefaults.default_ageing_range) {
			report.set_filter_value("range", frappe.boot.sysdefaults.default_ageing_range);
		}
	},
};

frappe.provide("erpnext.accounts");

erpnext.accounts.toggle_create_pe_primary_action = function (report) {
	if (!report || !report.datatable || !frappe.model.can_create("Payment Entry")) return;

	const has_purchase_invoice = report.datatable.rowmanager
		.getCheckedRows()
		.some((i) => report.datatable.datamanager.data[i]?.voucher_type === "Purchase Invoice");

	if (has_purchase_invoice) {
		report.page.set_primary_action(__("Create Payment Entries"), () =>
			erpnext.accounts.create_payment_entries_from_payable_report(report)
		);
	} else {
		report.page.clear_primary_action();
	}
};

erpnext.accounts.create_payment_entries_from_payable_report = function (report) {
	const datatable = report.datatable;
	if (!datatable) return;

	const rows = datatable.rowmanager
		.getCheckedRows()
		.map((i) => datatable.datamanager.data[i])
		.filter((r) => r && r.voucher_type === "Purchase Invoice" && r.voucher_no);

	if (!rows.length) {
		frappe.msgprint(__("Select one or more Purchase Invoice rows"));
		return;
	}

	// build per-(supplier, party_account) summary to match backend grouping key
	const supplierMap = {};
	for (const r of rows) {
		const key = `${r.party}||${r.party_account}`;
		if (!supplierMap[key]) {
			supplierMap[key] = {
				supplier: r.party,
				party_account: r.party_account,
				count: 0,
				outstanding: 0,
			};
		}
		supplierMap[key].count += 1;
		supplierMap[key].outstanding += r.outstanding || 0;
	}

	const overviewFields = [
		{
			fieldtype: "Data",
			fieldname: "supplier",
			label: __("Supplier"),
			read_only: 1,
			in_list_view: 1,
			width: 150,
		},
		{
			fieldtype: "Data",
			fieldname: "party_account",
			label: __("Payable Account"),
			read_only: 1,
			in_list_view: 1,
			width: 130,
		},
		{
			fieldtype: "Int",
			fieldname: "invoices",
			label: __("Invoices"),
			read_only: 1,
			in_list_view: 1,
			width: 70,
		},
		{
			fieldtype: "Float",
			fieldname: "payable_amount",
			label: __("Payable Amount"),
			read_only: 1,
			in_list_view: 1,
		},
	];

	const dialog = new frappe.ui.Dialog({
		title: __("Create Payment Entries"),
		fields: [
			{
				fieldname: "supplier_overview",
				fieldtype: "Table",
				label: __("Supplier Overview"),
				cannot_add_rows: true,
				cannot_delete_rows: true,
				fields: overviewFields,
				data: Object.values(supplierMap).map((d) => ({
					supplier: d.supplier,
					party_account: d.party_account,
					invoices: d.count,
					payable_amount: d.outstanding,
				})),
			},
		],
		primary_action_label: __("Create"),
		secondary_action_label: __("Cancel"),
		secondary_action() {
			dialog.hide();
			report.datatable.rowmanager.checkAll(false);
		},
		primary_action() {
			dialog.hide();

			const groupedKeys = new Set(
				Object.values(supplierMap)
					.filter((d) => d.count > 1)
					.map((d) => `${d.supplier}||${d.party_account}`)
			);

			const grouped_invoices = [];
			const ungrouped_invoices = [];
			for (const r of rows) {
				const payload = {
					voucher_no: r.voucher_no,
					supplier: r.party,
					party_account: r.party_account,
				};
				(groupedKeys.has(`${r.party}||${r.party_account}`)
					? grouped_invoices
					: ungrouped_invoices
				).push(payload);
			}

			const clearSelection = () => report.datatable.rowmanager.checkAll(false);

			frappe
				.call({
					method: "erpnext.accounts.bulk_payment.create_payment_entries",
					args: { grouped_invoices, ungrouped_invoices },
				})
				.then(clearSelection)
				.catch(clearSelection);
		},
	});
	dialog.show();
};

erpnext.utils.add_dimensions("Accounts Payable", 10);

function get_party_type_options() {
	let options = [];
	frappe.db
		.get_list("Party Type", { filters: { account_type: "Payable" }, fields: ["name"] })
		.then((res) => {
			res.forEach((party_type) => {
				options.push(party_type.name);
			});
		});
	return options;
}
