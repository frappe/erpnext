// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.hr");

erpnext.hr.ExpenseClaimController = frappe.ui.form.Controller.extend({
	make_bank_entry: function(frm) {
		var me = this;
		return frappe.call({
			method: "erpnext.hr.doctype.expense_claim.expense_claim.make_bank_entry",
			args: {
				"docname": frm.doc.name,
			},
			callback: function(r) {
				var doc = frappe.model.sync(r.message);
				frappe.set_route('Form', 'Journal Entry', r.message.name);
			}
		});
	},

	expense_type: function(doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(!doc.company) {
			d.expense_type = "";
			frappe.msgprint(__("Please set the Company"));
			this.frm.refresh_fields()
			return;
		}

		return frappe.call({
			method: "erpnext.hr.doctype.expense_claim.expense_claim.get_expense_claim_account",
			args: {
				"expense_claim_type": d.expense_type,
				"company": doc.company
			},
			callback: function(r) {
				if (r.message) {
					d.default_account = r.message.account;
				}
			}
		});
	}
})

frappe.ui.form.on("Expense Claim", {

	onload: function(frm) {
		if(!frm.doc.approval_status)
			frm.set_value("approval_status", "Draft")

		if (frm.doc.__islocal) {
			frm.set_value("posting_date", frappe.datetime.get_today());
			if(frm.doc.amended_from)
				frm.set_value("approval_status", "Draft");
			erpnext.hr.expense_claim.clear_sanctioned(frm.doc);
		}

		frm.fields_dict.employee.get_query = function(frm,cdt,cdn) {
			return{
				query: "erpnext.controllers.queries.employee_query"
			}
		};

		frm.set_query("exp_approver", function() {
			return {
				query: "erpnext.hr.doctype.expense_claim.expense_claim.get_expense_approver"
			};
		});

		frm.fields_dict['task'].get_query = function(frm) {
			return {
				filters:{
					'project': frm.doc.project
				}
			}
		};

		frm.add_fetch('employee', 'company', 'company');
		frm.add_fetch('employee','employee_name','employee_name');

		frm.cscript.calculate_total =  function(doc) {
			doc.total_claimed_amount = 0;
			doc.total_sanctioned_amount = 0;
			$.each((doc.expenses || []), function(i, d) {
				doc.total_claimed_amount += d.claim_amount;
				doc.total_sanctioned_amount += d.sanctioned_amount;
			});

			refresh_field("total_claimed_amount");
			refresh_field('total_sanctioned_amount');

		};

	},
	refresh: function(frm) {
		erpnext.hr.expense_claim.set_help(frm);

		if(!frm.doc.__islocal) {
			frm.toggle_enable("exp_approver", frm.doc.approval_status=="Draft");
			frm.toggle_enable("approval_status", (frm.doc.exp_approver==frappe.session.user && frm.doc.docstatus==0));

			if (frm.doc.docstatus==0 && frm.doc.exp_approver==frappe.session.user && frm.doc.approval_status=="Approved")
				frm.savesubmit();

			if (frm.doc.docstatus===1 && frm.doc.approval_status=="Approved") {
				if (cint(frm.doc.total_amount_reimbursed) < cint(frm.doc.total_sanctioned_amount) && frappe.model.can_create("Journal Entry")) {
					frm.add_custom_button(__("Bank Entry"), function() {
						frm.cscript.make_bank_entry(frm);
					}, __("Make"));
					frm.page.set_inner_btn_group_as_primary(__("Make"));
				}

				/* eslint-disable */
				// no idea how `me` works here
				if (cint(frm.doc.total_amount_reimbursed) > 0 && frappe.model.can_read("Journal Entry")) {
					frm.add_custom_button(__('Bank Entries'), function() {
						frappe.route_options = {
							"Journal Entry Account.reference_type": frm.doc.doctype,
							"Journal Entry Account.reference_name": frm.doc.name,
							company: frm.doc.company
						};
						frappe.set_route("List", "Journal Entry");
					}, __("View"));
				}
				/* eslint-enable */
			}
		}
		frm.toggle_display("summary_section", (frm.doc.__unsaved === undefined));

		if(frm.doc.docstatus == 1) {
			frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}
		frm.script_manager.trigger("toggle_fields")

	},
	validate: function(frm) {
		frm.cscript.calculate_total(frm.doc);
	},
	calculate_total_amount: function(frm) {
		frm.cscript.calculate_total(frm.doc);
	},
	on_submit: function(frm) {
		if(cint(frappe.boot.notification_settings && frappe.boot.notification_settings.expense_claim)) {
			frm.email_doc(frappe.boot.notification_settings.expense_claim_message);
		}
	},
	setup: function(frm) {
		frm.script_manager.trigger("set_query_for_cost_center")
		frm.script_manager.trigger("set_query_for_payable_account")
		frm.add_fetch("company", "cost_center", "cost_center");
		frm.add_fetch("company", "default_payable_account", "payable_account");
	},
	get_unclaimed_button: function(frm) {
		if (frm.doc.employee){
			frappe.call({
				method: "erpnext.hr.doctype.expense_claim.expense_claim.get_unpaid_receipts",
				args: {
					employee: frm.doc.employee,
					company: frm.doc.company
				},
				callback: function(r) {
					if(r.message)
					{
						console.log(r);
						for( var i = 0; i < r.message.length;i++)
						{
							var obj = r.message[i];
							if (!frm.doc.expenses.some(function(e) {return e.receipt == obj.name})) {
								var new_row = frm.add_child("expenses");
								for (var property in obj) {
									if (property === "name") {
										new_row.receipt = obj[property];
									}
									else{
										new_row[property] = obj[property];
									}
								}
							}
						}
					}
					refresh_field("expenses");

				}
			});
		} else {
			msgprint(__("Make sure the employee and company are filled out"));
		}
	},
	set_query_for_cost_center: function(frm) {
		frm.fields_dict["cost_center"].get_query = function() {
			return {
				filters: {
					"company": frm.doc.company
				}
			}
		}
	},

	set_query_for_payable_account: function(frm) {
		frm.fields_dict["payable_account"].get_query = function() {
			return {
				filters: {
					"root_type": "Liability",
					"account_type": "Payable"
				}
			}
		}
	},

	is_paid: function(frm) {
		frm.script_manager.trigger("toggle_fields");
	},

	toggle_fields: function(frm) {
		frm.toggle_reqd("mode_of_payment", frm.doc.is_paid);
	}
});

$.extend(cur_frm.cscript, new erpnext.hr.ExpenseClaimController({frm: cur_frm}));





erpnext.hr.expense_claim = {
	set_title: function(frm) {
		if (!frm.doc.task) {
			frm.set_value("title", frm.doc.employee_name);
		}
		else {
			frm.set_value("title", frm.doc.employee_name + " for "+ frm.doc.task);
		}
	},
	clear_sanctioned: function(doc) {
		var val = doc.expenses || [];
		for(var i = 0; i<val.length; i++){
			val[i].sanctioned_amount ='';
		}

		doc.total_sanctioned_amount = '';
		refresh_many(['sanctioned_amount', 'total_sanctioned_amount']);
	},
	set_help: function(frm) {
		frm.set_intro("");
		if((frm.doc.__islocal && !in_list(frappe.user_roles, "HR User")) ||(frm.doc.__unsaved)) {

			frm.set_intro(__("Fill the form and save it"))
		} else {
			if(frm.doc.docstatus==0 && frm.doc.approval_status=="Draft") {
				if(frappe.session.user==frm.doc.exp_approver) {
					frm.set_intro(__("You are the Expense Approver for this record. Please Update the 'Status' and Save"));
				} else {
					frm.set_intro(__("Expense Claim is pending approval. Only the Expense Approver can update status."));
				}
			}
		}
	}
}


frappe.ui.form.on("Expense Claim Detail", {
	claim_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		var doc = frm.doc;

		if((!child.sanctioned_amount) || (child.sanctioned_amount > child.claim_amount)){
			frappe.model.set_value(cdt, cdn, 'sanctioned_amount', child.claim_amount)
		}

		frappe.model.set_value(cdt, cdn, 'sanctioned_tax', child.tax_amount * child.sanctioned_amount / child.claim_amount)


		frm.cscript.calculate_total(doc);
	},
	tax_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		var doc = frm.doc;
		frappe.model.set_value(cdt, cdn, 'sanctioned_tax', child.tax_amount * child.sanctioned_amount / child.claim_amount)

		frm.cscript.calculate_total(doc);
	},

	sanctioned_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		var doc = frm.doc;
		frappe.model.set_value(cdt, cdn, 'sanctioned_tax', child.tax_amount * child.sanctioned_amount / child.claim_amount)
		frm.cscript.calculate_total(doc);
	}
});



frappe.ui.form.on("Expense Claim", "employee_name", function(frm) {
	erpnext.hr.expense_claim.set_title(frm);
});

frappe.ui.form.on("Expense Claim", "task", function(frm) {
	erpnext.hr.expense_claim.set_title(frm);
});


