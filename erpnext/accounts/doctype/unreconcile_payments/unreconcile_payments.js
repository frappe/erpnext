// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Unreconcile Payments", {
	refresh(frm) {
		frm.set_query("voucher_type", function() {
			return {
				filters: {
					name: "Payment Entry"
				}
			}
		});


		frm.set_query("voucher_no", function(doc) {
			return {
				filters: {
					company: doc.company,
					docstatus: 1
				}
			}
		});

	},
});
