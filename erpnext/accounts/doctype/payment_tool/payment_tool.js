// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");

erpnext.accounts.PaymentToolController = frappe.ui.form.Controller.extend({
	onload: function() {	

		var help_content = '<i class="icon-hand-right"></i> Note:<br>'+
			'<ul>If payment is not made against any reference, make Journal Voucher manually.</ul>';
		this.frm.set_value("make_jv_help", help_content);
	},

	get_outstanding_vouchers: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'get_outstanding_vouchers',
			callback: function(r, rt) {
				refresh_field("payment_tool_voucher_details");
			}
		});
	},
	
	payment_amount: function() {
		this.calculate_total_payment_amount();	
	},

	payment_tool_voucher_details_remove: function() {
		this.calculate_total_payment_amount();
	},

	calculate_total_payment_amount: function(){
		var me = this;
		var total_amount = 0;
		
		$.each(me.frm.doc.payment_tool_voucher_details || [], function(i, row) {
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