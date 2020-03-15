// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Closing Voucher', {
	onload: function(frm) {
		frm.set_query("pos_profile", function(doc) {
			return {
				filters: { 'user': doc.user }
			};
		});

		frm.set_query("user", function(doc) {
			return {
				query: "erpnext.selling.doctype.pos_closing_voucher.pos_closing_voucher.get_cashiers",
				filters: { 'parent': doc.pos_profile }
			};
		});

		frm.set_query("pos_opening_voucher", function(doc) {
			return { filters: { 'status': 'Open', 'docstatus': 1 } };
		});
		
		if (frm.doc.docstatus === 0) frm.set_value("period_end_date", frappe.datetime.now_datetime());
		if (frm.doc.docstatus === 1) set_html_data(frm);
	},

	pos_opening_voucher(frm) {
		if (frm.doc.pos_opening_voucher && frm.doc.period_start_date && frm.doc.period_end_date && frm.doc.user)
			frm.trigger("get_pos_invoices");
	},

	get_pos_invoices(frm) {
		frappe.call({
			method: 'erpnext.selling.doctype.pos_closing_voucher.pos_closing_voucher.get_pos_invoices',
			args: {
				start: frappe.datetime.get_datetime_as_string(frm.doc.period_start_date),
				end: frm.doc.period_end_date,
				user: frm.doc.user
			},
			callback: (r) => {
				let pos_docs = r.message;
				reset_values(frm);
				set_form_data(pos_docs, frm)
				refresh_fields(frm)
				set_html_data(frm)
			}
		})
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
});

function set_form_data(data, frm) {
	data.forEach(d => {
		add_to_pos_transaction(d, frm);
		if (d.is_return) frm.doc.expense_amount -= flt(d.grand_total);
		if (!d.is_return) frm.doc.total_amount += flt(d.grand_total);
		frm.doc.grand_total += flt(d.grand_total);
		frm.doc.net_total += flt(d.net_total);
		frm.doc.total_quantity += flt(d.total_qty);
		add_to_payments(d, frm);
		add_to_taxes(d, frm);
	});
}

function add_to_pos_transaction(d, frm) {
	frm.add_child("pos_transactions", {
		pos_invoice: d.name,
		posting_date: d.posting_date,
		grand_total: d.grand_total,
		customer: d.customer
	})
}

function add_to_payments(d, frm) {
	d.payments.forEach(p => {
		const payment = frm.doc.payment_reconciliation.find(pay => pay.mode_of_payment === p.mode_of_payment);
		if (payment) {
			payment.collected_amount += flt(p.amount);
		} else {
			frm.add_child("payment_reconciliation", {
				mode_of_payment: p.mode_of_payment,
				collected_amount: p.amount
			})
		}
	})
}

function add_to_taxes(d, frm) {
	console.log(d.taxes)
	d.taxes.forEach(t => {
		const tax = frm.doc.taxes.find(tx => tx.account_head === t.account_head && tx.rate === t.rate);
		if (tax) {
			tax.amount += flt(t.tax_amount); 
		} else {
			frm.add_child("taxes", {
				account_head: t.account_head,
				rate: t.rate,
				amount: t.tax_amount
			})
		}
	})
}

function reset_values(frm) {
	frm.set_value("pos_transactions", []);
	frm.set_value("payment_reconciliation", []);
	frm.set_value("taxes", []);
	frm.set_value("expense_amount", 0);
	frm.set_value("grand_total", 0);
	frm.set_value("net_total", 0);
	frm.set_value("total_quantity", 0);
}

function refresh_fields(frm) {
	frm.refresh_field("pos_transactions");
	frm.refresh_field("payment_reconciliation");
	frm.refresh_field("taxes");
	frm.refresh_field("expense_amount");
	frm.refresh_field("grand_total");
	frm.refresh_field("net_total");
	frm.refresh_field("total_quantity");
}

function set_html_data(frm) {
	frappe.call({
		method: "get_payment_reconciliation_details",
		doc: frm.doc,
		callback: (r) => {
			frm.get_field("payment_reconciliation_details").$wrapper.html(r.message);
		}
	})
}

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
					refresh_field("total_amount");

					frm.get_field("payment_reconciliation_details").$wrapper.html(r.message);
				}
			}
		});
	}

};
