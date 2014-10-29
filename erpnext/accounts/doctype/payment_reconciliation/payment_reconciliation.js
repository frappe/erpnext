// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");

erpnext.accounts.PaymentReconciliationController = frappe.ui.form.Controller.extend({

	onload: function() {
		var me = this
		this.frm.set_query('party_account', function() {
			if(!me.frm.doc.company) {
				msgprint(__("Please select company first"));
			} else {
				return{
					filters:[
						['Account', 'company', '=', me.frm.doc.company],
						['Account', 'group_or_ledger', '=', 'Ledger'],
						['Account', 'master_type', 'in', ['Customer', 'Supplier']]
					]
				};
			}

		});

		this.frm.set_query('bank_cash_account', function() {
			if(!me.frm.doc.company) {
				msgprint(__("Please select company first"));
			} else {
				return{
					filters:[
						['Account', 'company', '=', me.frm.doc.company],
						['Account', 'group_or_ledger', '=', 'Ledger'],
						['Account', 'account_type', 'in', ['Bank', 'Cash']]
					]
				};
			}
		});
	},

	get_unreconciled_entries: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'get_unreconciled_entries',
			callback: function(r, rt) {
				var invoices = [];

				$.each(me.frm.doc.payment_reconciliation_invoices || [], function(i, row) {
						if (row.invoice_number && !inList(invoices, row.invoice_number))
							invoices.push(row.invoice_number);
				});

				frappe.meta.get_docfield("Payment Reconciliation Payment", "invoice_number",
					me.frm.doc.name).options = invoices.join("\n");

				$.each(me.frm.doc.payment_reconciliation_payments || [], function(i, p) {
					if(!inList(invoices, cstr(p.invoice_number))) p.invoice_number = null;
				});

				refresh_field("payment_reconciliation_payments");
			}
		});

	},

	reconcile: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'reconcile'
		});
	}

});

$.extend(cur_frm.cscript, new erpnext.accounts.PaymentReconciliationController({frm: cur_frm}));

cur_frm.add_fetch('party_account', 'master_type', 'party_type')
