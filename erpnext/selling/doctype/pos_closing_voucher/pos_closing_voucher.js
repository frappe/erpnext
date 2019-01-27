// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Closing Voucher', {
	onload: function(frm) {
		frm.set_query("pos_profile", function(doc) {
			return {
				filters: {
					'user': doc.user
				}
			};
		});

		frm.set_query("user", function(doc) {
			return {
				query: "erpnext.selling.doctype.pos_closing_voucher.pos_closing_voucher.get_cashiers",
				filters: {
					'parent': doc.pos_profile
				}
			};
		});
	},

	total_amount: function(frm) {
		get_difference_amount(frm);
	},
	custody_amount: function(frm){
		get_difference_amount(frm);
	},
	expense_amount: function(frm){
		get_difference_amount(frm);
	},
	refresh: function(frm) {
		get_closing_voucher_details(frm);
	},
	period_start_date: function(frm) {
		get_closing_voucher_details(frm);
	},
	period_end_date: function(frm) {
		get_closing_voucher_details(frm);
	},
	company: function(frm) {
		get_closing_voucher_details(frm);
	},
	pos_profile: function(frm) {
		get_closing_voucher_details(frm);
	},
	user: function(frm) {
		get_closing_voucher_details(frm);
	},
});

frappe.ui.form.on('POS Closing Voucher Details', {
	collected_amount: function(doc, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "difference", row.collected_amount - row.expected_amount);
	}
});

var get_difference_amount = function(frm){
	frm.doc.difference = frm.doc.total_amount - frm.doc.custody_amount - frm.doc.expense_amount;
	refresh_field("difference");
};

var get_closing_voucher_details = function(frm) {
	if (frm.doc.period_end_date && frm.doc.period_start_date && frm.doc.company && frm.doc.pos_profile && frm.doc.user) {
		frappe.call({
			method: "get_closing_voucher_details",
			doc: frm.doc,
			callback: function(r) {
				if (r.message) {
					refresh_field("payment_reconciliation");
					refresh_field("sales_invoices_summary");
					refresh_field("taxes");

					refresh_field("grand_total");
					refresh_field("net_total");
					refresh_field("total_quantity");

					frm.get_field("payment_reconciliation_details").$wrapper.html(r.message);
				}
			}
		});
	}

};
