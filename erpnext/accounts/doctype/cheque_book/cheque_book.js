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
		// Cheque numbers keep their leading zeros, so pad them to six digits
		["cheque_start_no", "cheque_end_no"].forEach((fieldname) =>
			frm.fields_dict[fieldname].$input
				?.attr({ inputmode: "numeric", pattern: "[0-9]*" })
				.off(".cheque_number")
				.on("input.cheque_number", (e) => {
					e.target.value = e.target.value.replace(/\D/g, "");
				})
				.on("blur.cheque_number", (e) => {
					if (/^\d+$/.test(e.target.value)) {
						frm.set_value(fieldname, BigInt(e.target.value).toString().padStart(6, "0"));
					}
				})
		);
	},

	cheque_start_no(frm) {
		set_no_of_cheques(frm);
	},

	cheque_end_no(frm) {
		set_no_of_cheques(frm);
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		// a finished book has no free cheque to enable or disable
		if (frm.doc.status !== "Finished" && frm.perm[0]?.submit) {
			const disabled = frm.doc.status === "Disabled";
			frm.add_custom_button(
				disabled ? __("Enable") : __("Disable"),
				() =>
					frm
						.set_value("status", disabled ? "Submitted" : "Disabled")
						.then(() => frm.save("Update")),
				__("Actions")
			);
		}

		show_cheques(frm);
	},
});

function set_no_of_cheques(frm) {
	const { cheque_start_no: start, cheque_end_no: end } = frm.doc;
	const valid = /^\d+$/.test(start || "") && /^\d+$/.test(end || "");
	const count = valid ? Number(BigInt(end) - BigInt(start) + 1n) : 0;
	frm.set_value("no_of_cheques", count > 0 ? count : 0);
}

async function show_cheques(frm) {
	await frappe.require("embedded_list.bundle.js");
	// the wrapper is emptied so that a form refresh does not stack lists
	const wrapper = frm.get_field("cheques_html").$wrapper.empty();
	const cheques = new frappe.ui.EmbeddedList({
		wrapper,
		doctype: "Cheque",
		filters: { cheque_book: frm.doc.name },
		fields: [
			"name",
			"cheque_no",
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
			this._all_data.forEach((row) => (row.cheque_status = __(get_cheque_status(row))));
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
				color: (row) => CHEQUE_STATUS_COLOR[get_cheque_status(row)],
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

	const [, free, issued] = await Promise.all([
		cheques.refresh(),
		frappe.db.count("Cheque", { filters: { cheque_book: frm.doc.name, status: "Available" } }),
		frappe.db.count("Cheque", { filters: { cheque_book: frm.doc.name, status: "Issued" } }),
	]);
	const total = frm.doc.no_of_cheques;
	frm.dashboard.set_headline(
		__("Total: {0} · Free: {1} · Issued: {2} · Cancelled: {3}", [
			total,
			free,
			issued,
			total - free - issued,
		])
	);
}

const CHEQUE_STATUS_COLOR = {
	Available: "blue",
	Issued: "green",
	PDC: "orange",
	Cleared: "green",
	Cancelled: "red",
};

// An issued cheque dated after today is post dated, so the bank does not pay it yet
function get_cheque_status(row) {
	if (row.status !== "Issued") return row.status;
	if (row.clearance_date) return "Cleared";
	return row.cheque_date > frappe.datetime.get_today() ? "PDC" : "Issued";
}

function compare_cheque_nos(a, b) {
	return BigInt(a) < BigInt(b) ? -1 : BigInt(a) > BigInt(b) ? 1 : 0;
}
