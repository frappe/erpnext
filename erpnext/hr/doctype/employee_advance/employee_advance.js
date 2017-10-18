// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Advance', {
	setup: function(frm) {
		frm.add_fetch("employee", "company", "company");
		
		frm.set_query("approver", function() {
			return {
				query: "erpnext.hr.doctype.expense_claim.expense_claim.get_expense_approver"
			};
		});
	},
	
	refresh: function(frm) {
		frm.toggle_enable("approval_status",
			(frm.doc.approver==frappe.session.user && frm.doc.docstatus==0));
			
		if (frm.doc.docstatus===1 && frm.doc.approval_status=="Approved"
				&& (frm.doc.paid_amount < frm.doc.advance_amount)
				&& frappe.model.can_create("Payment Entry")) {
			frm.add_custom_button(__('Payment'),
				function() { frm.events.make_payment_entry(frm); }, __("Make"));
		}
	},
	
	make_payment_entry: function(frm) {
		var method = "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry";
		// if(frm.doc.__onload && frm.doc.__onload.make_payment_via_journal_entry) {
		// 	method = "erpnext.hr.doctype.expense_claim.expense_claim.make_bank_entry"
		// }
		return frappe.call({
			method: method,
			args: {
				"dt": frm.doc.doctype,
				"dn": frm.doc.name
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},
});
