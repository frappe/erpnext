// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

wn.provide("erpnext.hr");

erpnext.hr.ExpenseClaimController = wn.ui.form.Controller.extend({
	make_bank_voucher: function() {
		var me = this;
		return wn.call({
			method: "accounts.doctype.journal_voucher.journal_voucher.get_default_bank_cash_account",
			args: {
				"company": cur_frm.doc.company,
				"voucher_type": "Bank Voucher"
			},
			callback: function(r) {
				var jv = wn.model.make_new_doc_and_get_name('Journal Voucher');
				jv = locals['Journal Voucher'][jv];
				jv.voucher_type = 'Bank Voucher';
				jv.company = cur_frm.doc.company;
				jv.remark = 'Payment against Expense Claim: ' + cur_frm.doc.name;
				jv.fiscal_year = cur_frm.doc.fiscal_year;

				var d1 = wn.model.add_child(jv, 'Journal Voucher Detail', 'entries');
				d1.debit = cur_frm.doc.total_sanctioned_amount;

				// credit to bank
				var d1 = wn.model.add_child(jv, 'Journal Voucher Detail', 'entries');
				d1.account = r.message[0].account;
				d1.credit = cur_frm.doc.total_sanctioned_amount;
				d1.balance = r.message[0].balance;

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
			query:"controllers.queries.employee_query"
		}	
	}

	return cur_frm.call({
		method:"hr.utils.get_expense_approver_list",
		callback: function(r) {
			cur_frm.set_df_property("exp_approver", "options", r.message);
		}
	});
}

cur_frm.cscript.clear_sanctioned = function(doc) {
	var val = getchildren('Expense Claim Detail', doc.name, 
		'expense_voucher_details', doc.doctype);
	for(var i = 0; i<val.length; i++){
		val[i].sanctioned_amount ='';
	}

	doc.total_sanctioned_amount = '';
	refresh_many(['sanctioned_amount', 'total_sanctioned_amount']);	
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){
	cur_frm.set_intro("");
	if(doc.__islocal && !in_list(user_roles, "HR User")) {
		cur_frm.set_intro("Fill the form and save it")
	} else {
		if(doc.docstatus==0 && doc.approval_status=="Draft") {
			if(user==doc.exp_approver) {
				cur_frm.set_intro("You are the Expense Approver for this record. Please Update the 'Status' and Save");
				cur_frm.toggle_enable("approval_status", true);
			} else {
				cur_frm.set_intro("Expense Claim is pending approval. Only the Expense Approver can update status.");
				cur_frm.toggle_enable("approval_status", false);
				if(!doc.__islocal && cur_frm.frm_head.appframe.buttons.Submit) 
					cur_frm.frm_head.appframe.buttons.Submit.toggle(false);
			}
		} else {
			if(doc.approval_status=="Approved") {
				cur_frm.set_intro("Expense Claim has been approved.");
				if(doc.docstatus==0) cur_frm.savesubmit();
				if(doc.docstatus==1) cur_frm.add_custom_button("Make Bank Voucher", 
					cur_frm.cscript.make_bank_voucher);
			} else if(doc.approval_status=="Rejected") {
				cur_frm.set_intro("Expense Claim has been rejected.");
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
	$.each(wn.model.get("Expense Claim Detail", {parent:doc.name}), function(i, d) {
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
	if(cint(wn.boot.notification_settings && wn.boot.notification_settings.expense_claim)) {
		cur_frm.email_doc(wn.boot.notification_settings.expense_claim_message);
	}
}