// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Lease Agreement", {
	setup(frm) {
		frm.set_query("lease_expense_account", function () {
			return {
				filters: {
					is_group: 0,
					company: frm.doc.company,
				},
			};
		});
	},

	lease_term_months(frm) {
		if (frm.doc.use_lease_term) {
			frm.trigger("calculate_end_date");
		}
	},

	lease_start_date(frm) {
		if (frm.doc.use_lease_term) {
			frm.trigger("calculate_end_date");
		}
	},

	calculate_end_date(frm) {
		if (!frm.doc.lease_term_months || !frm.doc.lease_start_date) return;

		let lease_end_date = frappe.datetime.add_months(frm.doc.lease_start_date, frm.doc.lease_term_months);

		lease_end_date = frappe.datetime.add_days(lease_end_date, -1);
		frm.set_value("lease_end_date", lease_end_date);
	},
});
