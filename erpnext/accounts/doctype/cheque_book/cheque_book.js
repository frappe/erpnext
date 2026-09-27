// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cheque Book", {
	setup(frm) {
		frm.set_query("bank_account", () => ({
			filters: { is_company_account: 1, disabled: 0 },
		}));
	},

	onload_post_render(frm) {
		// the cheque numbers are Data fields, so keep them digits only
		["cheque_start_no", "cheque_end_no", "no_of_cheques"].forEach((fieldname) =>
			frm.fields_dict[fieldname].$input?.on("input", (e) => {
				e.target.value = e.target.value
					.replace(/\D/g, "")
					.slice(0, fieldname === "no_of_cheques" ? 10 : 6);
			})
		);
	},

	cheque_start_no(frm) {
		set_missing_range_value(frm, "cheque_start_no");
	},

	cheque_end_no(frm) {
		set_missing_range_value(frm, "cheque_end_no");
	},

	no_of_cheques(frm) {
		set_missing_range_value(frm, "no_of_cheques");
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		frm.add_custom_button(
			__("Issue Cancel Cheque"),
			() => {
				const doc = frappe.model.get_new_doc("Cancelled Cheque");
				doc.cheque_book = frm.doc.name;
				// reloaded because cancelling a cheque can move Next Cheque No and finish the book
				frappe.ui.form.make_quick_entry("Cancelled Cheque", () => frm.reload_doc(), null, doc);
			},
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

		// not awaited, the form refresh waits for this trigger
		show_cheques(frm);
	},

	async bank_account(frm) {
		if (!frm.is_new() || !frm.doc.bank_account || frm.doc.cheque_book_no) return;

		frm.set_value(
			"cheque_book_no",
			await frappe.xcall("erpnext.accounts.doctype.cheque_book.cheque_book.get_next_cheque_book_no", {
				bank_account: frm.doc.bank_account,
			})
		);
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
		filters: { cheque_book: frm.doc.name },
		fields: ["name", "cheque_no", "creation", "reason", "remarks", "payment_entry", "owner"],
		order_by: "cheque_no asc",
		empty_message: __("No cheque of this book is cancelled."),
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

	// counted from the range, so a book saved before this field existed still adds up
	const total = Number(BigInt(frm.doc.cheque_end_no) - BigInt(frm.doc.cheque_start_no) + 1n);
	const issued = frm.issued_cheques.data.length;
	const cancelled = frm.cancelled_cheques.data.length;
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

// any two of start no, end no and number of cheques give the third
function set_missing_range_value(frm, changed) {
	const { cheque_start_no: start, cheque_end_no: end, no_of_cheques: count } = frm.doc;
	if (["cheque_start_no", "cheque_end_no"].includes(changed)) {
		const value = frm.doc[changed];
		if (/^\d{1,6}$/.test(value) && value.length < 6) {
			frm.set_value(changed, value.padStart(6, "0"));
			return;
		}
	}

	if (changed !== "no_of_cheques" && start && end) {
		if (!/^\d+$/.test(start) || !/^\d+$/.test(end)) return;
		const total = BigInt(end) - BigInt(start) + 1n;
		if (total > 0n && total <= 2147483647n) frm.set_value("no_of_cheques", Number(total));
	} else if (changed !== "cheque_end_no" && start && count) {
		if (!/^\d+$/.test(start)) return;
		frm.set_value("cheque_end_no", pad(BigInt(start) + BigInt(count) - 1n));
	} else if (changed !== "cheque_start_no" && end && count) {
		if (!/^\d+$/.test(end)) return;
		frm.set_value("cheque_start_no", pad(BigInt(end) - BigInt(count) + 1n));
	}
}

function pad(value) {
	// leave an invalid range to the server, which explains what is wrong
	return value < 0n || value > 999999n ? "" : String(value).padStart(6, "0");
}
