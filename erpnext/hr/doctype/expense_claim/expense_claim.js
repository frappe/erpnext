// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.hr");

erpnext.hr.ExpenseClaimController = frappe.ui.form.Controller.extend({
	make_bank_voucher: function() {
		var me = this;
		return frappe.call({
			method: "erpnext.accounts.doctype.journal_voucher.journal_voucher.get_default_bank_cash_account",
			args: {
				"company": cur_frm.doc.company,
				"voucher_type": "Bank Voucher"
			},
			callback: function(r) {
				var jv = frappe.model.make_new_doc_and_get_name('Journal Voucher');
				jv = locals['Journal Voucher'][jv];
				jv.voucher_type = 'Bank Voucher';
				jv.company = cur_frm.doc.company;
				jv.remark = 'Payment against Expense Claim: ' + cur_frm.doc.name;
				jv.fiscal_year = cur_frm.doc.fiscal_year;

				var d1 = frappe.model.add_child(jv, 'Journal Voucher Detail', 'entries');
				d1.debit = cur_frm.doc.total_sanctioned_amount;

				// credit to bank
				var d1 = frappe.model.add_child(jv, 'Journal Voucher Detail', 'entries');
				d1.credit = cur_frm.doc.total_sanctioned_amount;
				if(r.message) {
					d1.account = r.message.account;
					d1.balance = r.message.balance;
				}

				loaddoc('Journal Voucher', jv.name);
			}
		});
	}
})

$.extend(cur_frm.cscript, new erpnext.hr.ExpenseClaimController({frm: cur_frm}));

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee','employee_name','employee_name');

cur_frm.cscript.onload = function(doc,cdt,cdn) {
	if(!doc.approval_status)
		cur_frm.set_value("approval_status", "Draft")

	if (doc.__islocal) {
		cur_frm.set_value("posting_date", dateutil.get_today());
		if(doc.amended_from)
			cur_frm.set_value("approval_status", "Draft");
		cur_frm.cscript.clear_sanctioned(doc);
	}

	cur_frm.fields_dict.employee.get_query = function(doc,cdt,cdn) {
		return{
			query: "erpnext.controllers.queries.employee_query"
		}
	}
	var exp_approver = doc.exp_approver;
	return cur_frm.call({
		method: "erpnext.hr.utils.get_expense_approver_list",
		callback: function(r) {
			cur_frm.set_df_property("exp_approver", "options", r.message);
			if(exp_approver) cur_frm.set_value("exp_approver", exp_approver);
		}
	});
}

cur_frm.cscript.clear_sanctioned = function(doc) {
	var val = doc.expense_voucher_details || [];
	for(var i = 0; i<val.length; i++){
		val[i].sanctioned_amount ='';
	}

	doc.total_sanctioned_amount = '';
	refresh_many(['sanctioned_amount', 'total_sanctioned_amount']);
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){
	cur_frm.cscript.set_help(doc);

	if(!doc.__islocal) {
		cur_frm.toggle_enable("exp_approver", (doc.owner==user && doc.approval_status=="Draft"));
		cur_frm.toggle_enable("approval_status", (doc.exp_approver==user && doc.docstatus==0));

		if(!doc.__islocal && user!=doc.exp_approver)
			cur_frm.frm_head.appframe.set_title_right("");

		if(doc.docstatus==0 && doc.exp_approver==user && doc.approval_status=="Approved")
			 cur_frm.savesubmit();

		if(doc.docstatus==1 && frappe.model.can_create("Journal Voucher"))
			 cur_frm.add_custom_button(__("Make Bank Voucher"),
			 	cur_frm.cscript.make_bank_voucher, frappe.boot.doctype_icons["Journal Voucher"]);
	}
}

cur_frm.cscript.set_help = function(doc) {
	cur_frm.set_intro("");
	if(doc.__islocal && !in_list(user_roles, "HR User")) {
		cur_frm.set_intro(__("Fill the form and save it"))
	} else {
		if(doc.docstatus==0 && doc.approval_status=="Draft") {
			if(user==doc.exp_approver) {
				cur_frm.set_intro(__("You are the Expense Approver for this record. Please Update the 'Status' and Save"));
			} else {
				cur_frm.set_intro(__("Expense Claim is pending approval. Only the Expense Approver can update status."));
			}
		} else {
			if(doc.approval_status=="Approved") {
				cur_frm.set_intro(__("Expense Claim has been approved."));
			} else if(doc.approval_status=="Rejected") {
				cur_frm.set_intro(__("Expense Claim has been rejected."));
			}
		}
	}
}

cur_frm.cscript.validate = function(doc) {
	cur_frm.cscript.calculate_total(doc);
}

cur_frm.cscript.calculate_total = function(doc,cdt,cdn){
	doc.total_claimed_amount = 0;
	doc.total_sanctioned_amount = 0;
	$.each((doc.expense_voucher_details || []), function(i, d) {
		doc.total_claimed_amount += d.claim_amount;
		if(d.sanctioned_amount==null) {
			d.sanctioned_amount = d.claim_amount;
		}
		doc.total_sanctioned_amount += d.sanctioned_amount;
	});

	refresh_field("total_claimed_amount");
	refresh_field('total_sanctioned_amount');

}

cur_frm.cscript.calculate_total_amount = function(doc,cdt,cdn){
	cur_frm.cscript.calculate_total(doc,cdt,cdn);
}
cur_frm.cscript.claim_amount = function(doc,cdt,cdn){
	cur_frm.cscript.calculate_total(doc,cdt,cdn);

	var child = locals[cdt][cdn];
	refresh_field("sanctioned_amount", child.name, child.parentfield);
}
cur_frm.cscript.sanctioned_amount = function(doc,cdt,cdn){
	cur_frm.cscript.calculate_total(doc,cdt,cdn);
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(frappe.boot.notification_settings && frappe.boot.notification_settings.expense_claim)) {
		cur_frm.email_doc(frappe.boot.notification_settings.expense_claim_message);
	}
}
