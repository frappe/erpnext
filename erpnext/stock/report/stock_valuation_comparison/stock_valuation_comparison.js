// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const REPORT_METHOD = "erpnext.stock.report.stock_valuation_comparison.stock_valuation_comparison";

const DIFFERENCE_FIELDS = [
	"qty_difference",
	"stock_value_difference_difference",
	"valuation_rate_difference",
	"stock_value_difference_in_balance",
];

frappe.query_reports["Stock Valuation Comparison"] = {
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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				return {
					filters: { is_stock_item: 1 },
				};
			},
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function () {
				return {
					filters: { company: frappe.query_report.get_filter_value("company") },
				};
			},
		},
		{
			fieldname: "show",
			label: __("Show"),
			fieldtype: "Select",
			options: [
				{
					label: __("First Difference per Item-Warehouse"),
					value: "First Difference per Item-Warehouse",
				},
				{ label: __("All Differences"), value: "All Differences" },
				{ label: __("All Entries"), value: "All Entries" },
			],
			default: "First Difference per Item-Warehouse",
		},
		{
			fieldname: "tolerance",
			label: __("Ignore Differences Below"),
			fieldtype: "Float",
			default: 0.01,
		},
		{
			fieldname: "show_adjusted_differences",
			label: __("Show Differences Settled by Adjustment Entries"),
			fieldtype: "Check",
			default: 0,
		},
	],

	get_datatable_options(options) {
		return Object.assign(options, { checkboxColumn: true });
	},

	onload(report) {
		const group = __("Fix Differences");
		report.page.add_inner_button(__("Repost"), () => repost_differences(report), group);
		report.page.add_inner_button(__("Adjustment Entry"), () => make_adjustment_entry(report), group);
	},

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (DIFFERENCE_FIELDS.includes(column.fieldname) && data && data[column.fieldname]) {
			value = `<span style="color: var(--red-500)">${value}</span>`;
		}

		return value;
	},
};

function get_differences_to_fix(report) {
	// the checked rows, or every row shown when none is checked
	const checked = report.get_checked_items();
	const rows = checked.length ? checked : report.data || [];
	const entries = rows.filter((row) => row.has_difference).map((row) => row.stock_ledger_entry);

	if (!entries.length) {
		frappe.msgprint(__("There are no differences to fix."));
	}

	return entries;
}

function get_item_warehouse_list(rows, detail) {
	const items = rows.map(
		(row) =>
			`<li>${__("{0} in {1}", [
				frappe.utils.escape_html(row.item_code).bold(),
				frappe.utils.escape_html(row.warehouse).bold(),
			])}${detail ? ": " + detail(row) : ""}</li>`
	);
	return `<ul>${items.join("")}</ul>`;
}

function repost_differences(report) {
	const company = report.get_filter_value("company");
	const stock_ledger_entries = get_differences_to_fix(report);
	if (!stock_ledger_entries.length) return;

	frappe.call({
		method: `${REPORT_METHOD}.get_repost_preview`,
		args: { company, stock_ledger_entries },
		callback: (r) => {
			const to_repost = r.message.filter((row) => !row.pending_repost);
			const pending = r.message.filter((row) => row.pending_repost);

			let message = "";
			if (pending.length) {
				message += `<p>${__("These already have a pending repost and are left out:")}</p>`;
				message += get_item_warehouse_list(pending, (row) => row.pending_repost);
			}

			if (!to_repost.length) {
				frappe.msgprint(message);
				return;
			}

			message += `<p>${__("Repost Item Valuation will be made for:")}</p>`;
			message += get_item_warehouse_list(to_repost, (row) =>
				__("from {0}", [frappe.datetime.str_to_user(row.posting_date)])
			);

			const past_fiscal_years = [
				...new Set(to_repost.filter((row) => row.is_past_fiscal_year).map((row) => row.fiscal_year)),
			];
			if (past_fiscal_years.length) {
				message += `<div class="alert alert-warning">${__(
					"Since you are reposting transactions from the previous fiscal year {0}, the closing balances of that fiscal year can change. The reposting might also take time to complete.",
					[past_fiscal_years.join(", ").bold()]
				)}</div>`;
			}

			message += `<p>${__("Do you want to continue?")}</p>`;

			frappe.confirm(message, () => {
				frappe.call({
					method: `${REPORT_METHOD}.make_repost_entries`,
					args: { company, stock_ledger_entries },
					freeze: true,
					callback: (r) => show_repost_result(report, r.message),
				});
			});
		},
	});
}

function show_repost_result(report, result) {
	let message = "";
	if (result.created.length) {
		message += `<p>${__("Reposting has been queued for:")}</p>`;
		message += get_item_warehouse_list(result.created, (row) =>
			frappe.utils.get_form_link("Repost Item Valuation", row.repost, true)
		);
	}

	if (result.not_created.length) {
		message += `<p>${__("Reposting could not be queued for:")}</p>`;
		message += get_item_warehouse_list(result.not_created, (row) => row.reason);
	}

	frappe.msgprint({
		title: __("Repost"),
		message,
		indicator: result.not_created.length ? "orange" : "green",
	});
	report.refresh();
}

function make_adjustment_entry(report) {
	const company = report.get_filter_value("company");
	const stock_ledger_entries = get_differences_to_fix(report);
	if (!stock_ledger_entries.length) return;

	const dialog = new frappe.ui.Dialog({
		title: __("Make Adjustment Entry"),
		fields: [
			{
				fieldtype: "HTML",
				options: `<p class="text-muted">${__(
					"The stock qty and value of the selected items are set right on this date, without reposting. Stock and accounting reports before it keep the old values, and no stock transaction can be posted before it for these items afterwards."
				)}</p>`,
			},
			{
				fieldname: "posting_date",
				fieldtype: "Date",
				label: __("Adjustment Date"),
				reqd: 1,
				default: frappe.datetime.get_today(),
			},
			{
				fieldname: "posting_time",
				fieldtype: "Time",
				label: __("Adjustment Time"),
				reqd: 1,
				default: "00:00:00",
			},
			{
				fieldname: "expense_account",
				fieldtype: "Link",
				label: __("Difference Account"),
				options: "Account",
				description: __("Defaults to the company's Stock Adjustment Account"),
				get_query: () => ({ filters: { company, is_group: 0 } }),
			},
		],
		primary_action_label: __("Make"),
		primary_action(values) {
			dialog.hide();
			frappe.call({
				method: `${REPORT_METHOD}.make_adjustment_entry`,
				args: { company, stock_ledger_entries, ...values },
				freeze: true,
				callback: (r) => show_adjustment_result(r.message),
			});
		},
	});

	dialog.show();
}

function show_adjustment_result(result) {
	let message = "";
	if (result.not_adjusted.length) {
		message += `<p>${__("These cannot be settled by an Adjustment Entry and need a repost:")}</p>`;
		message += get_item_warehouse_list(result.not_adjusted, (row) => row.reason);
	}

	if (!result.adjustment_entry) {
		frappe.msgprint({ title: __("Adjustment Entry"), message, indicator: "orange" });
		return;
	}

	if (message) {
		frappe.msgprint({ title: __("Adjustment Entry"), message, indicator: "orange" });
	}

	frappe.set_route("Form", "Stock Reconciliation", result.adjustment_entry);
}
