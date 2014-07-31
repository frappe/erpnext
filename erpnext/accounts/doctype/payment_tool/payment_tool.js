// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");

erpnext.accounts.PaymentToolController = frappe.ui.form.Controller.extend({
	get_outstanding_vouchers: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'get_outstanding_vouchers',
			callback: function(r, rt) {
				refresh_field("outstanding_vouchers"); //Points to child table
			}
		});
	},
	
	payment_amount: function() {
		this.calculate_total_payment_amount();	
	},

	outstanding_vouchers_remove: function() {
		this.calculate_total_payment_amount();
	},

	calculate_total_payment_amount: function(){
		var me = this;
		var total_amount = 0;
		
		$.each(me.frm.doc.outstanding_vouchers || [], function(i, row) { //Points to child table
				if (row.payment_amount)
					total_amount = total_amount + row.payment_amount
		});

		me.frm.set_value("total_payment_amount", total_amount);
	},
	
	make_journal_voucher: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: "make_journal_voucher",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}


});

$.extend(cur_frm.cscript, new erpnext.accounts.PaymentToolController({frm: cur_frm}));