// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");

frappe.ui.form.on("Payment Reconciliation Payment", {
	invoice_number: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.invoice_number) {
			var parts = row.invoice_number.split(' | ');
			var invoice_type = parts[0];
			var invoice_number = parts[1];

			var invoice_amount = frm.doc.invoices.filter(function(d) {
				return d.invoice_type === invoice_type && d.invoice_number === invoice_number;
			})[0].outstanding_amount;

			frappe.model.set_value(cdt, cdn, "allocated_amount", Math.min(invoice_amount, row.amount));
		}
	}
});

erpnext.accounts.PaymentReconciliationController = frappe.ui.form.Controller.extend({
	onload: function() {
		var me = this;
		this.frm.set_query("party_type", function() {
			return{
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type"
			}
		});

		this.frm.set_query('receivable_payable_account', function() {
			if(!me.frm.doc.company || !me.frm.doc.party_type) {
				frappe.msgprint(__("Please select Company and Party Type first"));
			} else {
				return{
					filters: {
						"company": me.frm.doc.company,
						"is_group": 0,
						"account_type": (me.frm.doc.party_type == "Customer" ? "Receivable" : "Payable")
					}
				};
			}

		});

		this.frm.set_query('bank_cash_account', function() {
			if(!me.frm.doc.company) {
				frappe.msgprint(__("Please select Company first"));
			} else {
				return{
					filters:[
						['Account', 'company', '=', me.frm.doc.company],
						['Account', 'is_group', '=', 0],
						['Account', 'account_type', 'in', ['Bank', 'Cash']]
					]
				};
			}
		});
	},

	refresh: function() {
		this.frm.disable_save();
		this.toggle_primary_action();
	},

	onload_post_render: function() {
		this.toggle_primary_action();
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
				me.set_invoice_options();
				me.toggle_primary_action();
			}
		});

	},

	reconcile: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'reconcile',
			callback: function(r, rt) {
				me.set_invoice_options();
				me.toggle_primary_action();
			}
		});
	},

	set_invoice_options: function() {
		var me = this;
		var invoices = [];

		$.each(me.frm.doc.invoices || [], function(i, row) {
			if (row.invoice_number && !in_list(invoices, row.invoice_number))
				invoices.push(row.invoice_type + " | " + row.invoice_number);
		});

		if (invoices) {
			frappe.meta.get_docfield("Payment Reconciliation Payment", "invoice_number",
				me.frm.doc.name).options = "\n" + invoices.join("\n");

			$.each(me.frm.doc.payments || [], function(i, p) {
				if(!in_list(invoices, cstr(p.invoice_number))) p.invoice_number = null;
			});
		}

		refresh_field("payments");
	},

	toggle_primary_action: function() {
		if ((this.frm.doc.payments || []).length) {
			this.frm.fields_dict.reconcile.$input
				&& this.frm.fields_dict.reconcile.$input.addClass("btn-primary");
			this.frm.fields_dict.get_unreconciled_entries.$input
				&& this.frm.fields_dict.get_unreconciled_entries.$input.removeClass("btn-primary");
		} else {
			this.frm.fields_dict.reconcile.$input
				&& this.frm.fields_dict.reconcile.$input.removeClass("btn-primary");
			this.frm.fields_dict.get_unreconciled_entries.$input
				&& this.frm.fields_dict.get_unreconciled_entries.$input.addClass("btn-primary");
		}
	}

});

$.extend(cur_frm.cscript, new erpnext.accounts.PaymentReconciliationController({frm: cur_frm}));
