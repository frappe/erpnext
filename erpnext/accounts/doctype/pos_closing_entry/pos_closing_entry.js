// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Closing Entry', {
	onload: function(frm) {
		frm.ignore_doctypes_on_cancel_all = ['POS Invoice Merge Log'];
		frm.set_query("pos_profile", function(doc) {
			return {
				filters: { 'user': doc.user }
			};
		});

		frm.set_query("user", function(doc) {
			return {
				query: "erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_cashiers",
				filters: { 'parent': doc.pos_profile }
			};
		});

		frm.set_query("pos_opening_entry", function(doc) {
			return { filters: { 'status': 'Open', 'docstatus': 1 } };
		});
		
		if (frm.doc.docstatus === 0 && !frm.doc.amended_from) frm.set_value("period_end_date", frappe.datetime.now_datetime());
		if (frm.doc.docstatus === 1) set_html_data(frm);
	},

	pos_opening_entry(frm) {
		if (frm.doc.pos_opening_entry && frm.doc.period_start_date && frm.doc.period_end_date && frm.doc.user) {
			reset_values(frm);
			frm.trigger("set_opening_amounts");
			frm.trigger("get_pos_invoices");
		}
	},

	set_opening_amounts(frm) {
		frappe.db.get_doc("POS Opening Entry", frm.doc.pos_opening_entry)
			.then(({ balance_details }) => {
				balance_details.forEach(detail => {
					frm.add_child("payment_reconciliation", {
						mode_of_payment: detail.mode_of_payment,
						opening_amount: detail.opening_amount,
						expected_amount: detail.opening_amount
					});
				})
			});
	},

	get_pos_invoices(frm) {
		frappe.call({
			method: 'erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_pos_invoices',
			args: {
				start: frappe.datetime.get_datetime_as_string(frm.doc.period_start_date),
				end: frappe.datetime.get_datetime_as_string(frm.doc.period_end_date),
				pos_profile: frm.doc.pos_profile,
				user: frm.doc.user
			},
			callback: (r) => {
				let pos_docs = r.message;
				set_form_data(pos_docs, frm);
				refresh_fields(frm);
				set_html_data(frm);
			}
		})
	}
});

cur_frm.cscript.before_pos_transactions_remove = function(doc, cdt, cdn) {
	const removed_row = locals[cdt][cdn];

	if (!removed_row.pos_invoice) return;

	frappe.db.get_doc("POS Invoice", removed_row.pos_invoice).then(doc => {
		cur_frm.doc.grand_total -= flt(doc.grand_total);
		cur_frm.doc.net_total -= flt(doc.net_total);
		cur_frm.doc.total_quantity -= flt(doc.total_qty);
		refresh_payments(doc, cur_frm, 1);
		refresh_taxes(doc, cur_frm, 1);
		refresh_fields(cur_frm);
		set_html_data(cur_frm);
	});
}

frappe.ui.form.on('POS Invoice Reference', {
	pos_invoice(frm, cdt, cdn) {
		const added_row = locals[cdt][cdn];

		if (!added_row.pos_invoice) return;

		frappe.db.get_doc("POS Invoice", added_row.pos_invoice).then(doc => {
			frm.doc.grand_total += flt(doc.grand_total);
			frm.doc.net_total += flt(doc.net_total);
			frm.doc.total_quantity += flt(doc.total_qty);
			refresh_payments(doc, frm);
			refresh_taxes(doc, frm);
			refresh_fields(frm);
			set_html_data(frm);
		});
	}
})

frappe.ui.form.on('POS Closing Entry Detail', {
	closing_amount: (frm, cdt, cdn) => {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "difference", flt(row.expected_amount - row.closing_amount))
	}
})

function set_form_data(data, frm) {
	data.forEach(d => {
		add_to_pos_transaction(d, frm);
		frm.doc.grand_total += flt(d.grand_total);
		frm.doc.net_total += flt(d.net_total);
		frm.doc.total_quantity += flt(d.total_qty);
		refresh_payments(d, frm);
		refresh_taxes(d, frm);
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

function refresh_payments(d, frm, remove) {
	d.payments.forEach(p => {
		const payment = frm.doc.payment_reconciliation.find(pay => pay.mode_of_payment === p.mode_of_payment);
		if (payment) {
			if (!remove) payment.expected_amount += flt(p.amount);
			else payment.expected_amount -= flt(p.amount);
		} else {
			frm.add_child("payment_reconciliation", {
				mode_of_payment: p.mode_of_payment,
				opening_amount: 0,
				expected_amount: p.amount
			})
		}
	})
}

function refresh_taxes(d, frm, remove) {
	d.taxes.forEach(t => {
		const tax = frm.doc.taxes.find(tx => tx.account_head === t.account_head && tx.rate === t.rate);
		if (tax) {
			if (!remove) tax.amount += flt(t.tax_amount);
			else tax.amount -= flt(t.tax_amount);
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
	frm.set_value("grand_total", 0);
	frm.set_value("net_total", 0);
	frm.set_value("total_quantity", 0);
}

function refresh_fields(frm) {
	frm.refresh_field("pos_transactions");
	frm.refresh_field("payment_reconciliation");
	frm.refresh_field("taxes");
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
