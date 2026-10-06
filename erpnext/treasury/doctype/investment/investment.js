// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investment", {
	setup(frm) {
		frm.set_query("investment_type", () => ({ filters: { is_active: 1 } }));
		frm.set_query("issuer", () => ({ filters: { is_active: 1 } }));
		frm.set_query("custodian", () => ({ filters: { is_active: 1 } }));

		for (const fieldname of erpnext.treasury.ACCOUNT_FIELDS) {
			frm.set_query(fieldname, () => ({
				filters: { company: frm.doc.company, is_group: 0 },
			}));
		}

		frm.set_query("cost_center", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Investment Transaction"), () => make_transaction(frm), __("Create"));

			if (["Deposit", "Bond"].includes(frm.doc.instrument_class)) {
				frm.add_custom_button(
					__("Investment Interest Accrual"),
					() =>
						frappe.new_doc("Investment Interest Accrual", {
							investment: frm.doc.name,
						}),
					__("Create")
				);
			}

			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}
	},
});

function make_transaction(frm) {
	frappe.new_doc("Investment Transaction", {
		investment: frm.doc.name,
		instrument_class: frm.doc.instrument_class,
		company: frm.doc.company,
		currency: frm.doc.currency,
		cost_center: frm.doc.cost_center,
	});
}
