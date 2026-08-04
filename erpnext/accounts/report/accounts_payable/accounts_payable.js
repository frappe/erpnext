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
			label: __("Report Date"),
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
			fieldname: "age_as_on",
			label: __("Age as on"),
			fieldtype: "Select",
			options: "Report Date\nToday",
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
			fieldtype: "MultiSelectList",
			options: "Supplier Group",
			get_data: function (txt) {
				return frappe.db.get_link_options("Supplier Group", txt);
			},
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
				onCheckRow: () => toggle_create_pe_button(frappe.query_report),
			},
		});
	},

	after_refresh: function (report) {
		report.datatable?.rowmanager?.checkAll(false);
		toggle_create_pe_button(report);
	},

	onload: function (report) {
		if (frappe.model.can_create("Payment Entry")) {
			report.create_pe_btn = report.page
				.add_inner_button(__("Create Payment Entries"), function () {
					create_payment_entries_from_payable_report(report);
				})
				.toggle(false);
		}

		report.page.add_inner_button(__("Accounts Payable Summary"), function () {
			var filters = report.get_values();
			frappe.set_route("query-report", "Accounts Payable Summary", { company: filters.company });
		});

		if (frappe.boot.sysdefaults.default_ageing_range) {
			report.set_filter_value("range", frappe.boot.sysdefaults.default_ageing_range);
		}
	},
};

function toggle_create_pe_button(report) {
	if (!report || !report.create_pe_btn || !report.datatable) return;

	const has_purchase_invoice = report.datatable.rowmanager
		.getCheckedRows()
		.some((i) => report.datatable.datamanager.data[i]?.voucher_type === "Purchase Invoice");

	report.create_pe_btn.toggle(has_purchase_invoice);
}

function create_payment_entries_from_payable_report(report) {
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

	// validate against live state: only unpaid/partly-paid invoices with real outstanding are payable
	frappe.call({
		method: "erpnext.accounts.bulk_payment.get_payable_invoices",
		args: { invoices: rows.map((r) => ({ voucher_no: r.voucher_no })) },
		callback: ({ message }) => {
			const { payable = [], excluded = [], currency } = message || {};
			if (!payable.length) {
				frappe.msgprint(__("None of the selected invoices are payable"));
				return;
			}
			show_create_payment_entries_dialog(report, payable, excluded, currency);
		},
	});
}

function show_create_payment_entries_dialog(report, payable, excluded, currency) {
	// group by (supplier, party_account) for the overview — matches the backend grouping key
	const supplierMap = {};
	for (const inv of payable) {
		const key = `${inv.supplier}||${inv.party_account}`;
		if (!supplierMap[key]) {
			supplierMap[key] = {
				supplier: inv.supplier,
				party_account: inv.party_account,
				count: 0,
				outstanding: 0,
			};
		}
		supplierMap[key].count += 1;
		supplierMap[key].outstanding += inv.outstanding || 0;
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

	const fields = [];
	if (excluded.length) {
		fields.push({ fieldtype: "HTML", fieldname: "excluded_note", options: excluded_note_html(excluded) });
	}
	fields.push({
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
	});

	const pe_count = Object.keys(supplierMap).length;
	const grand_total = Object.values(supplierMap).reduce((sum, d) => sum + d.outstanding, 0);
	fields.push({
		fieldtype: "HTML",
		fieldname: "summary_footer",
		options: summary_footer_html(pe_count, grand_total, currency),
	});

	const dialog = new frappe.ui.Dialog({
		title: __("Create Payment Entries"),
		fields: fields,
		primary_action_label: __("Create"),
		secondary_action_label: __("Cancel"),
		secondary_action() {
			dialog.hide();
			report.datatable.rowmanager.checkAll(false);
		},
		primary_action() {
			dialog.hide();

			// backend re-derives supplier/party_account and grouping from live data
			const invoices = payable.map((inv) => ({ voucher_no: inv.voucher_no }));

			const clearSelection = () => report.datatable.rowmanager.checkAll(false);

			frappe
				.call({
					method: "erpnext.accounts.bulk_payment.create_payment_entries",
					args: { invoices },
				})
				.then(clearSelection)
				.catch(clearSelection);
		},
	});
	dialog.show();
}

function summary_footer_html(pe_count, grand_total, currency) {
	return `<div style="
			display: flex;
			justify-content: space-between;
			align-items: center;
			margin-top: var(--margin-sm);
			font-size: var(--text-sm);
		">
			<span class="text-muted">${__("Payment Entries are created as drafts for your review")}</span>
			<span>${__("{0} Payment Entries", [pe_count])} ·
				<strong>${format_currency(grand_total, currency)}</strong></span>
		</div>`;
}

function excluded_note_html(excluded) {
	const counts = {};
	for (const e of excluded) {
		counts[e.reason] = (counts[e.reason] || 0) + 1;
	}
	const summary = Object.entries(counts)
		.map(([reason, n]) => `${n} ${reason}`)
		.join(", ");
	return `<div style="
			background-color: var(--bg-yellow);
			color: var(--text-on-yellow);
			font-size: var(--text-sm);
			border-radius: var(--border-radius);
			padding: var(--padding-sm) var(--padding-md);
			margin-bottom: var(--margin-sm);
		">
			<span style="font-weight: var(--weight-medium);">${__("{0} invoice(s) excluded", [
				excluded.length,
			])}</span>: ${frappe.utils.escape_html(summary)}
		</div>`;
}

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
