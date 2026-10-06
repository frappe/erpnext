// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investment Renewal", {
	setup(frm) {
		frm.set_query("original_investment", () => ({
			filters: {
				docstatus: 1,
				status: ["in", ["Partially Redeemed", "Matured", "Redeemed"]],
			},
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(__("General Ledger"), () => show_general_ledger(frm), __("View"));
		}

		if (frm.doc.docstatus === 1 && !frm.doc.new_investment) {
			frm.add_custom_button(
				__("Investment"),
				() =>
					frappe.model.open_mapped_doc({
						method: "erpnext.treasury.doctype.investment_renewal.investment_renewal.make_new_investment",
						frm: frm,
					}),
				__("Create")
			);
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}
	},

	principal_renewed(frm) {
		set_total_renewed(frm);
	},

	interest_renewed(frm) {
		set_total_renewed(frm);
	},
});

// a renewal posts no GL of its own, so show the original investment's ledger up to the renewal date
function show_general_ledger(frm) {
	frappe.db
		.get_value("Investment", frm.doc.original_investment, ["investment_account", "purchase_date"])
		.then(({ message }) => {
			frappe.route_options = {
				company: frm.doc.company,
				account: message.investment_account,
				from_date: message.purchase_date,
				to_date: frm.doc.renewal_date,
				ignore_prepared_report: true,
			};
			frappe.set_route("query-report", "General Ledger");
		});
}

function set_total_renewed(frm) {
	frm.set_value("total_renewed", flt(frm.doc.principal_renewed) + flt(frm.doc.interest_renewed));
}
