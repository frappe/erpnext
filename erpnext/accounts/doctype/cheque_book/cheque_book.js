// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cheque Book", {
	setup(frm) {
		frm.add_fetch("bank_account", "account", "current_account");
		frm.set_query("bank_account", () => ({
			filters: { is_company_account: 1, disabled: 0 },
		}));
	},

	bank_account(frm) {
		if (!frm.is_new() || !frm.doc.bank_account) return;

		return frm.call({ doc: frm.doc, method: "set_cheque_book_no", freeze: true });
	},

	onload_post_render(frm) {
		// Cheque leaf numbers retain their leading zeros.
		["cheque_book_no", "cheque_start_no", "cheque_end_no"].forEach((fieldname) =>
			frm.fields_dict[fieldname].$input
				?.attr({ inputmode: "numeric", pattern: "[0-9]*" })
				.off(".cheque_number")
				.on("input.cheque_number", (e) => {
					e.target.value = e.target.value.replace(/\D/g, "");
				})
				.on("blur.cheque_number", (e) => {
					if (fieldname !== "cheque_book_no" && /^\d+$/.test(e.target.value)) {
						return frm.set_value(fieldname, BigInt(e.target.value).toString().padStart(6, "0"));
					}
				})
		);
	},

	cheque_start_no(frm) {
		return set_missing_range_value(frm, "cheque_start_no");
	},

	cheque_end_no(frm) {
		return set_missing_range_value(frm, "cheque_end_no");
	},

	no_of_cheques(frm) {
		return set_missing_range_value(frm, "no_of_cheques");
	},

	refresh(frm) {
		frm.set_df_property(
			"no_of_cheques",
			"description",
			frm.is_new() ? __("Enter any two of Cheque Start No, Cheque End No and Number of Cheques") : ""
		);
		if (frm.doc.docstatus !== 1) return;

		frm.add_custom_button(
			__("Issue Cancel Cheque"),
			() => frappe.new_doc("Cancelled Cheque", { cheque_book: frm.doc.name }),
			__("Actions")
		);

		// a finished book has nothing to enable
		if (frm.doc.status !== "Finished") {
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

async function show_cheques(frm) {
	await frappe.require("embedded_list.bundle.js");

	frm.issued_cheques = make_list(frm, "issued_cheques_html", {
		doctype: "Payment Entry",
		filters: { cheque_book: frm.doc.name, docstatus: 1 },
		fields: ["name", "reference_no", "reference_date", "party_name", "paid_amount", "clearance_date"],
		order_by: "reference_no asc",
		empty_message: __("No cheque of this book is issued yet."),
		// the badge column reads a fieldname, and a stored value is searchable too
		before_render() {
			this._all_data.sort((a, b) => compare_cheque_nos(a.reference_no, b.reference_no));
			this._all_data.forEach((row) => (row.cheque_status = __(get_cheque_status(row))));
		},
		columns: [
			{ label: __("Cheque No"), fieldname: "reference_no" },
			{
				label: __("Cheque Date"),
				render: (row) => frappe.datetime.str_to_user(row.reference_date),
			},
			{ label: __("Amount"), render: (row) => format_currency(row.paid_amount) },
			{
				label: __("Status"),
				fieldname: "cheque_status",
				type: "badge",
				color: (row) => CHEQUE_STATUS_COLOR[get_cheque_status(row)],
			},
			{ label: __("Party"), fieldname: "party_name" },
			{
				label: __("Payment Entry"),
				fieldname: "name",
				type: "link",
				route: (row) => ["Form", "Payment Entry", row.name],
			},
		],
	});

	frm.cancelled_cheques = make_list(frm, "cancelled_cheques_html", {
		doctype: "Cancelled Cheque",
		filters: { cheque_book: frm.doc.name, docstatus: 1 },
		fields: ["name", "cheque_no", "creation", "reason", "remarks", "payment_entry", "owner"],
		order_by: "cheque_no asc",
		empty_message: __("No cheque of this book is cancelled."),
		before_render() {
			this._all_data.sort((a, b) => compare_cheque_nos(a.cheque_no, b.cheque_no));
		},
		columns: [
			{ label: __("Cheque No"), fieldname: "cheque_no" },
			{ label: __("Cancelled On"), render: (row) => frappe.datetime.str_to_user(row.creation) },
			{ label: __("Reason"), fieldname: "reason", type: "badge" },
			{ label: __("Remarks"), fieldname: "remarks" },
			{
				// rendered, not a link column, because most cancelled cheques have no Payment Entry
				label: __("Payment Entry"),
				render: (row) =>
					row.payment_entry
						? frappe.utils.get_form_link("Payment Entry", row.payment_entry, true)
						: "",
			},
			// user_info, not frappe.user.full_name, which says "You" for your own rows
			{ label: __("Cancelled By"), render: (row) => frappe.user_info(row.owner).fullname },
		],
	});

	await Promise.all([frm.issued_cheques.refresh(), frm.cancelled_cheques.refresh()]);

	const total = frm.doc.no_of_cheques;
	const issued = frm.issued_cheques.data.length;
	const cancelled = frm.cancelled_cheques.data.length;
	// Use the loaded rows for the same numeric free-count rule as the server, without another request.
	const occupied = new Set(
		[
			...frm.issued_cheques.data.map((row) => row.reference_no),
			...frm.cancelled_cheques.data.map((row) => row.cheque_no),
		]
			.filter((no) => /^\d+$/.test(no || ""))
			.map((no) => BigInt(no).toString())
	).size;
	frm.dashboard.set_headline(
		__("Total: {0} · Issued: {1} · Cancelled: {2} · Free: {3}", [
			total,
			issued,
			cancelled,
			total - occupied,
		])
	);
}

const CHEQUE_STATUS_COLOR = { Cleared: "green", PDC: "amber", Issued: "blue" };

// a cheque dated ahead of today is post dated, so the bank will not pay it yet
function get_cheque_status(row) {
	if (row.clearance_date) return "Cleared";
	return row.reference_date > frappe.datetime.get_today() ? "PDC" : "Issued";
}

function make_list(frm, fieldname, options) {
	// the wrapper is emptied so a form refresh does not stack tables
	const wrapper = frm.get_field(fieldname).$wrapper.empty();
	return new frappe.ui.EmbeddedList({ wrapper, ...options });
}

async function set_missing_range_value(frm, changed) {
	if (frm.updating_cheque_range) return;
	const { cheque_start_no: start, cheque_end_no: end, no_of_cheques: count } = frm.doc;
	if ((start && !/^\d+$/.test(start)) || (end && !/^\d+$/.test(end))) return;
	const values = {};
	if (changed !== "no_of_cheques" && start && end) {
		const total = BigInt(end) - BigInt(start) + 1n;
		if (total < 1n || total > 2147483647n) return;
		values.no_of_cheques = Number(total);
	} else if (Number.isInteger(count) && count > 0) {
		if (start) {
			values.cheque_end_no = (BigInt(start) + BigInt(count) - 1n).toString().padStart(6, "0");
		} else if (end) {
			const first = BigInt(end) - BigInt(count) + 1n;
			if (first < 0n) return;
			values.cheque_start_no = first.toString().padStart(6, "0");
		}
	}
	frm.updating_cheque_range = true;
	try {
		await frm.set_value(values);
	} finally {
		frm.updating_cheque_range = false;
	}
}

function compare_cheque_nos(a, b) {
	return BigInt(a) < BigInt(b) ? -1 : BigInt(a) > BigInt(b) ? 1 : 0;
}
