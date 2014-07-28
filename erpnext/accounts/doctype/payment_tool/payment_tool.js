// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");

erpnext.accounts.PaymentToolController = frappe.ui.form.Controller.extend({

	get_outstanding_vouchers: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'get_outstanding_vouchers'
		});
	},

	make_sales_invoice: function() {
		frappe.model.open_mapped_doc({
			doc: me.frm.doc,
			method: 'make_journal_voucher'
		})
	},


});

$.extend(cur_frm.cscript, new erpnext.accounts.PaymentToolController({frm: cur_frm}));