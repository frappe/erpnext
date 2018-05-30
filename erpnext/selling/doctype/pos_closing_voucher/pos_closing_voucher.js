// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Closing Voucher', {
	refresh: function(frm) {
		get_z_ticket(frm);
	},
	period_start_date: function(frm) {
		if (frm.doc.pos_profile && frm.doc.period_start_date) {
			get_closing_voucher_details(frm);
		}
	},
	period_end_date: function(frm) {
		if (frm.doc.pos_profile && frm.doc.period_end_date) {
			get_closing_voucher_details(frm);
		}
	},
	company: function(frm) {
		if (frm.doc.pos_profile && frm.doc.company) {
			get_closing_voucher_details(frm);
		}
	},
	pos_profile: function(frm) {
		if (frm.doc.pos_profile) {
			get_closing_voucher_details(frm);
		}
	}
});

frappe.ui.form.on('POS Closing Voucher Details', {
	collected_amount: function(doc, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "difference", row.collected_amount - row.expected_amount);
	}
});


var get_closing_voucher_details = function(frm) {
	frappe.call({
		method: "erpnext.selling.doctype.pos_closing_voucher.pos_closing_voucher.get_closing_voucher_details",
		args: {
			docname: frm.doc.name,
			from_date: frm.doc.period_start_date,
			to_date: frm.doc.period_end_date,
			company: frm.doc.company,
			pos_profile: frm.doc.pos_profile,
			is_pos: 1
		},
		callback: function(r) {
			if (r.message) {
				let mop = r.message.mop;
				frm.set_value("payment_reconciliation", "");
				mop.forEach(function(item){
					frm.add_child('payment_reconciliation', {'mode_of_payment': item.name, 'expected_amount': item.amount});
				});
				refresh_field("payment_reconciliation");

				let invoices = r.message.invoices;
				frm.set_value("sales_invoices_summary", "");
				invoices.forEach(function(item){
					frm.add_child('sales_invoices_summary', {'invoice': item.name, 'qty_of_items': item.pos_total_qty, 'grand_total': item.grand_total});
				});
				refresh_field("sales_invoices_summary");

				let taxes = r.message.taxes;
				frm.set_value("taxes", "");
				taxes.forEach(function(item){
					frm.add_child('taxes', {'rate': item.rate, 'amount': item.amount});
				});
				refresh_field("taxes");

				let sales_summary = r.message.sales_summary;
				frm.set_value("grand_total", sales_summary.grand_total);
				refresh_field("grand_total");
				frm.set_value("net_total", sales_summary.net_total);
				refresh_field("net_total");
				frm.set_value("total_quantity", sales_summary.total_qty);
				refresh_field("total_quantity");
			}
		}
	});
};

var get_z_ticket = function(frm) {

	frappe.call({
		method: "erpnext.selling.doctype.pos_closing_voucher.pos_closing_voucher.get_payment_reconciliation_details",
		args: {
			doc: frm.doc
		},
		callback: function(r) {
			if (r.message) {
					frm.get_field("payment_reconciliation_details").$wrapper.html(r.message);
			}
		}
	});
};
