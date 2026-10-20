// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const PREVIEW_TRIGGERS = [
	"transaction_type",
	"from_share_number",
	"to_share_number",
	"face_value_per_share",
	"rate_per_share",
	"clearing_account",
	"bank_account",
];

frappe.ui.form.on("Share Transaction", {
	refresh(frm) {
		frm.trigger("render_accounting_preview");
		frm.trigger("add_payment_entry_button");
		frm.trigger("show_clearance_status");
	},

	async company(frm) {
		if (!frm.doc.company) return;
		const { message } = await frappe.db.get_value("Company", frm.doc.company, "default_currency");
		if (message) {
			await frm.set_value("currency", message.default_currency);
		}
		frm.trigger("set_accounting_defaults");
	},

	async set_accounting_defaults(frm) {
		if (!frm.doc.company || frm.doc.docstatus) return;
		const { message } = await frappe.db.get_value("Share Accounting Settings", frm.doc.company, [
			"accounting_mode",
			"clearing_account",
			"default_bank_account",
		]);
		if (!message) return;
		await frm.set_value({
			accounting_mode: message.accounting_mode,
			clearing_account: message.clearing_account,
			bank_account: frm.doc.bank_account || message.default_bank_account,
		});
	},

	async mode_of_payment(frm) {
		const account = await get_mode_of_payment_account(frm, frm.doc.mode_of_payment);
		if (account) {
			frm.set_value("bank_account", account);
		}
	},

	setup(frm) {
		frm.set_query("clearing_account", () => get_account_query(frm));
		frm.set_query("bank_account", () => get_account_query(frm));
	},

	add_payment_entry_button(frm) {
		const needs_payment_entry =
			frm.doc.docstatus === 1 &&
			frm.doc.accounting_mode === "Clearing" &&
			["Issue", "Buyback", "Reissue"].includes(frm.doc.transaction_type) &&
			!frm.doc.payment_entry;
		if (!needs_payment_entry) return;
		frm.add_custom_button(__("Payment Entry"), () => make_payment_entry(frm), __("Create"));
	},

	async show_clearance_status(frm) {
		if (frm.doc.docstatus !== 1 || !frm.doc.payment_entry) return;
		const { message } = await frappe.db.get_value("Payment Entry", frm.doc.payment_entry, [
			"docstatus",
			"clearance_date",
		]);
		if (!message || message.docstatus !== 1) return;
		if (message.clearance_date) {
			const date = frappe.datetime.str_to_user(message.clearance_date);
			frm.dashboard.add_indicator(__("Cleared in bank on {0}", [date]), "green");
		} else {
			frm.dashboard.add_indicator(__("Not cleared in bank"), "orange");
		}
	},

	async render_accounting_preview(frm) {
		const wrapper = frm.fields_dict.accounting_preview?.$wrapper;
		if (!wrapper || !frm.doc.transaction_type || frm.doc.transaction_type === "Transfer") return;
		const { message } = await frm
			.call({ method: "get_accounting_preview", doc: frm.doc, silent: true })
			.catch(() => ({ message: null }));
		wrapper.html(message ? get_preview_html(frm, message) : get_preview_unavailable_html());
	},
});

PREVIEW_TRIGGERS.forEach((fieldname) => {
	frappe.ui.form.on("Share Transaction", {
		[fieldname](frm) {
			if (!frm.doc.docstatus) frm.trigger("render_accounting_preview");
		},
	});
});

function get_account_query(frm) {
	return {
		filters: {
			company: frm.doc.company,
			is_group: 0,
			disabled: 0,
			account_type: ["not in", ["Receivable", "Payable"]],
		},
	};
}

function make_payment_entry(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Create Payment Entry"),
		fields: [
			{
				fieldname: "mode_of_payment",
				fieldtype: "Link",
				options: "Mode of Payment",
				label: __("Mode of Payment"),
				default: frm.doc.mode_of_payment,
				async onchange() {
					const account = await get_mode_of_payment_account(frm, this.get_value());
					if (account) dialog.set_value("bank_account", account);
				},
			},
			{
				fieldname: "bank_account",
				fieldtype: "Link",
				options: "Account",
				label: __("Bank or Cash Account"),
				reqd: 1,
				default: frm.doc.bank_account,
				get_query: () => get_account_query(frm),
			},
			{
				fieldname: "posting_date",
				fieldtype: "Date",
				label: __("Payment Date"),
				reqd: 1,
				default: frappe.datetime.get_today(),
			},
			{
				fieldname: "reference_no",
				fieldtype: "Data",
				label: __("Cheque / Reference No"),
				default: frm.doc.reference_no,
			},
			{
				fieldname: "reference_date",
				fieldtype: "Date",
				label: __("Cheque / Reference Date"),
				default: frm.doc.reference_date,
			},
		],
		primary_action_label: __("Create"),
		async primary_action(values) {
			dialog.hide();
			const { message } = await frm.call({ method: "make_payment_entry", doc: frm.doc, args: values });
			frappe.set_route("Form", "Payment Entry", message);
		},
	});
	dialog.show();
}

function get_mode_of_payment_account(frm, mode_of_payment) {
	return frappe.xcall(
		"erpnext.accounts.shareholding.share_transaction_accounting.get_mode_of_payment_account",
		{
			mode_of_payment,
			company: frm.doc.company,
		}
	);
}

function get_preview_html(frm, rows) {
	if (!rows.length) return get_preview_unavailable_html();
	const body = rows
		.map(
			(row) => `<tr>
				<td>${frappe.utils.escape_html(row.account)}</td>
				<td class="text-right">${row.debit ? format_currency(row.debit, frm.doc.currency) : ""}</td>
				<td class="text-right">${row.credit ? format_currency(row.credit, frm.doc.currency) : ""}</td>
			</tr>`
		)
		.join("");
	return `<table class="table table-bordered table-sm">
		<thead><tr><th>${__("Account")}</th><th class="text-right">${__("Debit")}</th><th class="text-right">${__(
		"Credit"
	)}</th></tr></thead>
		<tbody>${body}</tbody>
	</table>`;
}

function get_preview_unavailable_html() {
	return `<p class="text-muted">${__(
		"The accounting impact is shown once the shares, rate and accounts are set."
	)}</p>`;
}
