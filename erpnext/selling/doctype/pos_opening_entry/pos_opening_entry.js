// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Opening Entry', {
	setup(frm) {
		if (frm.doc.docstatus == 0) {
			frm.trigger('set_posting_date_read_only');
			frm.set_value('period_start_date', frappe.datetime.now_datetime());
			frm.set_value('user', frappe.session.user);
		}

		frm.set_query("user", function(doc) {
			return {
				query: "erpnext.selling.doctype.pos_closing_entry.pos_closing_entry.get_cashiers",
				filters: { 'parent': doc.pos_profile }
			};
		});
	},

	refresh(frm) {
		// set default posting date / time
		if(frm.doc.docstatus == 0) {
			if(!frm.doc.posting_date) {
				frm.set_value('posting_date', frappe.datetime.nowdate());
			}
			frm.trigger('set_posting_date_read_only');
		}
	},

	set_posting_date_read_only(frm) {
		if(frm.doc.docstatus == 0 && frm.doc.set_posting_date) {
			frm.set_df_property('posting_date', 'read_only', 0);
		} else {
			frm.set_df_property('posting_date', 'read_only', 1);
		}
	},

	set_posting_date(frm) {
		frm.trigger('set_posting_date_read_only');
	},

	pos_profile: (frm) => {
		if (frm.doc.pos_profile) {
			frappe.db.get_doc("POS Profile", frm.doc.pos_profile)
				.then(({ payments }) => {
					if (payments.length) {
						frm.doc.balance_details = [];
						payments.forEach(({ mode_of_payment }) => {
							frm.add_child("balance_details", { mode_of_payment });
						})
						frm.refresh_field("balance_details");

						fetch_pos_closing_balance(frm);
					}
				});
		}
	}
});

function fetch_pos_closing_balance(frm) {
	const { pos_profile, user, company } = frm.doc

	frappe.db.get_list("POS Closing Entry", {
		filters: { company, pos_profile, user },
		limit: 1,
		order_by: 'period_end_date desc'
	}).then((res) => {
		if (!res) return;

		const pos_closing_entry = res[0];
		frappe.db.get_doc("POS Closing Entry", pos_closing_entry.name).then(({ payment_reconciliation }) => {
			payment_reconciliation.forEach(pay => {
				const balance_detail = frm.doc.balance_details.find(detail => detail.mode_of_payment === pay.mode_of_payment);
				if (!balance_detail) return;
				balance_detail.opening_amount = pay.closing_amount;
			});
			frappe.show_alert({
				message: __("Opening amount fetched from recent POS Closing."),
				indicator: 'green'
			})
			frm.refresh_field("balance_details");
		})
	})
}