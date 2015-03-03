// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");

erpnext.accounts.PaymentReconciliationController = frappe.ui.form.Controller.extend({

	onload: function() {
		var me = this
		this.frm.set_query('party_type', function() {
			return {
				filters: {
					"name": ["in", ["Customer", "Supplier"]]
				}
			};
		});

		this.frm.set_query('receivable_payable_account', function() {
			if(!me.frm.doc.company || !me.frm.doc.party_type) {
				msgprint(__("Please select Company and Party Type first"));
			} else {
				return{
					filters: {
						"company": me.frm.doc.company,
						"group_or_ledger": "Ledger",
						"account_type": (me.frm.doc.party_type == "Customer" ? "Receivable" : "Payable")
					}
				};
			}

		});

		this.frm.set_query('bank_cash_account', function() {
			if(!me.frm.doc.company) {
				msgprint(__("Please select Company first"));
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

	party: function() {
		var me = this
		if(!me.frm.doc.receivable_payable_account && me.frm.doc.party_type && me.frm.doc.party) {
			return frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					company: me.frm.doc.company,
					party_type: me.frm.doc.party_type,
					party: me.frm.doc.party
				},
				callback: function(r) {
					if(!r.exc && r.message) {
						me.frm.set_value("receivable_payable_account", r.message);
					}
				}
			});
		}
	},

	get_unreconciled_entries: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'get_unreconciled_entries',
			callback: function(r, rt) {
				var invoices = [];

				$.each(me.frm.doc.invoices || [], function(i, row) {
						if (row.invoice_number && !inList(invoices, row.invoice_number))
							invoices.push(row.invoice_number);
				});

				frappe.meta.get_docfield("Payment Reconciliation Payment", "invoice_number",
					me.frm.doc.name).options = invoices.join("\n");

				$.each(me.frm.doc.payments || [], function(i, p) {
					if(!inList(invoices, cstr(p.invoice_number))) p.invoice_number = null;
				});

				refresh_field("payments");
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
