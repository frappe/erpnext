// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investment Interest Accrual", {
	setup(frm) {
		frm.set_query("investment", () => ({
			filters: { docstatus: 1, instrument_class: ["in", ["Deposit", "Bond"]] },
		}));

		frm.set_query("cost_center", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
	},

	onload(frm) {
		if (frm.is_new() && frm.doc.investment && !frm.doc.from_date) {
			set_accrual_defaults(frm);
		}
	},

	refresh(frm) {
		erpnext.treasury.set_conversion_rate(frm);

		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(
				__("General Ledger"),
				() => erpnext.treasury.show_general_ledger(frm, frm.doc.posting_date),
				__("View")
			);
		}
	},

	investment(frm) {
		if (frm.doc.investment) {
			set_accrual_defaults(frm);
		}
	},

	to_date(frm) {
		if (frm.doc.to_date) {
			frm.set_value("posting_date", frm.doc.to_date);
		}
	},

	interest_amount(frm) {
		frm.set_value("variance", flt(frm.doc.interest_amount) - flt(frm.doc.estimated_interest));
	},

	currency(frm) {
		erpnext.treasury.set_conversion_rate(frm);
	},
});

// next accrual period with the estimate as the starting Interest Amount
function set_accrual_defaults(frm) {
	frappe
		.call({
			method: "erpnext.treasury.doctype.investment_interest_accrual.investment_interest_accrual.get_accrual_defaults",
			args: { investment: frm.doc.investment },
		})
		.then(({ message }) => {
			if (!message) return;

			frm.set_value({
				from_date: message.from_date,
				to_date: message.to_date,
				posting_date: message.posting_date,
				estimated_interest: message.interest_amount,
				interest_amount: message.interest_amount,
			});
		});
}
