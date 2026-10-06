// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investment Revaluation", {
	setup(frm) {
		frm.set_query("cost_center", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));

		frm.set_query("investment", "investments", () => ({
			filters: {
				company: frm.doc.company,
				docstatus: 1,
				instrument_class: ["in", ["Units", "Bond"]],
			},
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Investments"), () => get_investments(frm));
		}

		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(
				__("General Ledger"),
				() => erpnext.treasury.show_general_ledger(frm, frm.doc.revaluation_date),
				__("View")
			);
		}
	},

	company(frm) {
		frm.clear_table("investments");
		frm.refresh_field("investments");
	},
});

function get_investments(frm) {
	if (!frm.doc.company || !frm.doc.revaluation_date) {
		frappe.msgprint(__("Please set Company and Revaluation Date first"));
		return;
	}

	frm.call({
		doc: frm.doc,
		method: "set_investments",
		freeze: true,
		callback() {
			frm.dirty();
			frm.refresh_field("investments");
			if (!frm.doc.investments.length) {
				frappe.show_alert({ message: __("No investments to value"), indicator: "blue" });
			}
		},
	});
}
