// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investment Transaction", {
	setup(frm) {
		frm.set_query("investment", () => ({ filters: { docstatus: 1 } }));

		frm.set_query("cash_account", () => ({
			filters: {
				company: frm.doc.company,
				is_group: 0,
				account_type: ["in", ["Bank", "Cash"]],
			},
		}));

		frm.set_query("cost_center", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
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

		if (frm.doc.docstatus === 1) {
			add_create_buttons(frm);
		}
	},

	currency(frm) {
		erpnext.treasury.set_conversion_rate(frm);
	},
});

function add_create_buttons(frm) {
	// deposits have no market value to revalue
	if (frm.doc.instrument_class !== "Deposit") {
		frm.add_custom_button(__("Investment Revaluation"), () => make_revaluation(frm), __("Create"));
	}

	frappe.db.get_value("Investment", frm.doc.investment, "status").then(({ message }) => {
		if (["Partially Redeemed", "Matured", "Redeemed"].includes(message?.status)) {
			frm.add_custom_button(
				__("Investment Renewal"),
				() =>
					frappe.new_doc("Investment Renewal", {
						original_investment: frm.doc.investment,
					}),
				__("Create")
			);
		}
	});

	frm.page.set_inner_btn_group_as_primary(__("Create"));
}

function make_revaluation(frm) {
	frappe.new_doc("Investment Revaluation", { company: frm.doc.company }, (revaluation) => {
		const row = frappe.model.add_child(revaluation, "investments");
		row.investment = frm.doc.investment;
		row.instrument_class = frm.doc.instrument_class;
		row.investment_currency = frm.doc.currency;
	});
}
