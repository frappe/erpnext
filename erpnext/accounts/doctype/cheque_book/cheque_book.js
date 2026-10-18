// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cheque Book", {
	setup(frm) {
		frm.add_fetch("bank_account", "account", "current_account");
		frm.set_query("bank_account", () => ({
			filters: { is_company_account: 1, disabled: 0 },
		}));
	},

	onload_post_render(frm) {
		// cheque numbers are digits only
		["cheque_start_no", "cheque_end_no"].forEach((fieldname) =>
			frm.fields_dict[fieldname].$input
				?.attr({ inputmode: "numeric", pattern: "[0-9]*" })
				.off(".cheque_number")
				.on("input.cheque_number", (e) => {
					e.target.value = e.target.value.replace(/\D/g, "");
				})
				.on("blur.cheque_number", (e) => set_cheque_range(frm, fieldname, e.target.value))
		);
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		// a finished book has no free cheque to enable or disable
		if (frm.doc.status !== "Finished" && frm.perm[0]?.submit) {
			const disabled = frm.doc.status === "Disabled";
			frm.add_custom_button(
				disabled ? __("Enable") : __("Disable"),
				() => frm.call(disabled ? "enable" : "disable").then(() => frm.reload_doc()),
				__("Actions")
			);
		}

		show_cheques(frm);
	},
});

// The server pads the range and counts its cheques when the user leaves a range field.
// Frappe may not have stored the last keystrokes yet, so store the typed value first.
async function set_cheque_range(frm, fieldname, value) {
	await frm.set_value(fieldname, value);
	return frm.call("set_cheque_range");
}

async function show_cheques(frm) {
	// the Cheque meta brings cheque_list.js, which gives the status of each cheque
	await Promise.all([frappe.require("embedded_list.bundle.js"), frappe.model.with_doctype("Cheque")]);
	// the wrapper is emptied so that a form refresh does not stack lists
	const wrapper = frm.get_field("cheques_html").$wrapper.empty();
	const cheques = new frappe.ui.EmbeddedList({
		wrapper,
		doctype: "Cheque",
		filters: { cheque_book: frm.doc.name },
		fields: [
			"name",
			"cheque_no",
			"docstatus",
			"status",
			"cheque_date",
			"party_name",
			"amount",
			"currency",
			"payment_entry",
			"payment_entry.clearance_date as clearance_date",
			"cancellation_reason",
			"remarks",
		],
		order_by: "cheque_no asc",
		// the badge column reads a fieldname, and a stored value is searchable too
		before_render() {
			this._all_data.sort((a, b) => compare_cheque_nos(a.cheque_no, b.cheque_no));
			this._all_data.forEach((row) => {
				[row.cheque_status, row.status_color] = frappe.get_indicator(row, "Cheque");
			});
		},
		columns: [
			{
				label: __("Cheque No"),
				fieldname: "cheque_no",
				type: "link",
				route: (row) => ["Form", "Cheque", row.name],
			},
			{
				label: __("Status"),
				fieldname: "cheque_status",
				type: "badge",
				color: (row) => row.status_color,
			},
			{
				label: __("Cheque Date"),
				render: (row) => (row.cheque_date ? frappe.datetime.str_to_user(row.cheque_date) : ""),
			},
			{ label: __("Party"), fieldname: "party_name" },
			{
				label: __("Amount"),
				render: (row) => (row.payment_entry ? format_currency(row.amount, row.currency) : ""),
			},
			{
				// rendered, not a link column, because most cheques have no Payment Entry
				label: __("Payment Entry"),
				render: (row) =>
					row.payment_entry
						? frappe.utils.get_form_link("Payment Entry", row.payment_entry, true)
						: "",
			},
			{
				// a render column goes into the page as HTML, so escape the text users typed
				label: __("Reason"),
				render: (row) =>
					frappe.utils.escape_html(
						[row.cancellation_reason, row.remarks].filter(Boolean).join(": ")
					),
			},
		],
	});

	const book = { cheque_book: frm.doc.name };
	// an issued cheque dated after today is post dated, so the bank does not pay it yet
	const post_dated = { ...book, status: "Issued", cheque_date: [">", frappe.datetime.get_today()] };
	const [, free, issued, pdc] = await Promise.all([
		cheques.refresh(),
		frappe.db.count("Cheque", { filters: { ...book, status: "Available" } }),
		frappe.db.count("Cheque", { filters: { ...book, status: "Issued" } }),
		frappe.db.count("Cheque", { filters: post_dated }),
	]);
	const total = frm.doc.no_of_cheques;
	frm.dashboard.set_headline(
		__("Total: {0} · Free: {1} · Issued: {2} · PDC: {3} · Cancelled: {4}", [
			total,
			free,
			issued - pdc,
			pdc,
			total - free - issued,
		])
	);
}

function compare_cheque_nos(a, b) {
	return BigInt(a) < BigInt(b) ? -1 : BigInt(a) > BigInt(b) ? 1 : 0;
}
