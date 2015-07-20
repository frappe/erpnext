// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.hr");

erpnext.hr.ExpenseClaimController = frappe.ui.form.Controller.extend({
	make_bank_entry: function() {
		var me = this;
		return frappe.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_default_bank_cash_account",
			args: {
				"company": cur_frm.doc.company,
				"voucher_type": "Bank Entry"
			},
			callback: function(r) {
				var jv = frappe.model.make_new_doc_and_get_name('Journal Entry');
				jv = locals['Journal Entry'][jv];
				jv.voucher_type = 'Bank Entry';
				jv.company = cur_frm.doc.company;
				jv.remark = 'Payment against Expense Claim: ' + cur_frm.doc.name;
				jv.fiscal_year = cur_frm.doc.fiscal_year;
				var expense = cur_frm.doc.expenses || [];
				for(var i = 0; i < expense.length; i++){
					var d1 = frappe.model.add_child(jv, 'Journal Entry Account', 'accounts');
					d1.debit = expense[i].sanctioned_amount;
					d1.account = expense[i].default_account;
					d1.against_expense_claim = cur_frm.doc.name;
				}

				// credit to bank
				var d1 = frappe.model.add_child(jv, 'Journal Entry Account', 'accounts');
				d1.credit = cur_frm.doc.total_sanctioned_amount;
				d1.against_expense_claim = cur_frm.doc.name;
				if(r.message) {
					d1.account = r.message.account;
					d1.balance = r.message.balance;
				}

				loaddoc('Journal Entry', jv.name);
			}
		});
	}
})

$.extend(cur_frm.cscript, new erpnext.hr.ExpenseClaimController({frm: cur_frm}));

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee','employee_name','employee_name');
cur_frm.add_fetch('expense_type', 'default_account', 'default_account');

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
	};

	cur_frm.set_query("exp_approver", function() {
		return {
			query: "erpnext.hr.doctype.expense_claim.expense_claim.get_expense_approver"
		};
	});
}

cur_frm.cscript.clear_sanctioned = function(doc) {
	var val = doc.expenses || [];
	for(var i = 0; i<val.length; i++){
		val[i].sanctioned_amount ='';
	}

	doc.total_sanctioned_amount = '';
	refresh_many(['sanctioned_amount', 'total_sanctioned_amount']);
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){
	cur_frm.cscript.set_help(doc);

	if(!doc.__islocal) {
		cur_frm.toggle_enable("exp_approver", doc.approval_status=="Draft");
		cur_frm.toggle_enable("approval_status", (doc.exp_approver==user && doc.docstatus==0));

		if(doc.docstatus==0 && doc.exp_approver==user && doc.approval_status=="Approved")
			 cur_frm.savesubmit();

		if(doc.docstatus==1 && frappe.model.can_create("Journal Entry") &&
			cint(doc.total_amount_reimbursed) < cint(doc.total_sanctioned_amount))
			 cur_frm.add_custom_button(__("Make Bank Entry"),
			 	cur_frm.cscript.make_bank_entry, frappe.boot.doctype_icons["Journal Entry"]);
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
		}
	}
}

cur_frm.cscript.validate = function(doc) {
	cur_frm.cscript.calculate_total(doc);
}

cur_frm.cscript.calculate_total = function(doc,cdt,cdn){
	doc.total_claimed_amount = 0;
	doc.total_sanctioned_amount = 0;
	$.each((doc.expenses || []), function(i, d) {
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

erpnext.expense_claim = {
	set_title :function(frm) {
		if (!frm.doc.task) {
			frm.set_value("title", frm.doc.employee_name);
		}
		else {
			frm.set_value("title", frm.doc.employee_name + " for "+ frm.doc.task);
		}
	}
}

frappe.ui.form.on("Expense Claim", "employee_name", function(frm) {
	erpnext.expense_claim.set_title(frm);
});

frappe.ui.form.on("Expense Claim", "task", function(frm) {
	erpnext.expense_claim.set_title(frm);
});

cur_frm.fields_dict['task'].get_query = function(doc) {
	return {
		filters:{
			'project': doc.project
		}
	}	
}