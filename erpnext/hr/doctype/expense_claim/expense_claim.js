// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.hr");

erpnext.hr.ExpenseClaimController = class ExpenseClaimController extends frappe.ui.form.Controller {
	setup() {
		var me = this;

		me.frm.custom_make_buttons = {
			'Payment Entry': 'Payment'
		};

		if (me.frm.doc.__islocal) {
			me.frm.doc.posting_date = frappe.datetime.get_today();
		}

		me.frm.fields_dict.employee.get_query = function() {
			return {
				query: "erpnext.controllers.queries.employee_query"
			};
		};

		me.frm.set_query("expense_approver", function() {
			return {
				query: "erpnext.hr.doctype.department_approver.department_approver.get_approvers",
				filters: {
					employee: me.frm.doc.employee,
					doctype: me.frm.doc.doctype
				}
			};
		});
		me.frm.fields_dict["payable_account"].get_query = function() {
			return {
				filters: {
					"account_type": ["in", ["Payable", "Receivable"]],
					"company": me.frm.doc.company,
					"is_group": 0
				}
			};
		};

		me.frm.set_query("expense_account", "expenses", function(doc, cdt, cdn) {
			var d = frappe.get_doc(cdt, cdn);
			var filters = {
				company: me.frm.doc.company,
				is_group: 0
			};

			if (d.requires_purchase_invoice) {
				filters.account_type = "Payable";
			} else {
				filters.root_type = "Expense";
			}

			return {
				filters: filters
			};
		});

		me.frm.set_query("cost_center", "expenses", function() {
			return {
				filters: {
					"company": me.frm.doc.company,
					"is_group": 0
				}
			};
		});

		me.frm.set_query('task', 'expenses', function(doc, cdt, cdn) {
			var d = frappe.get_doc(cdt, cdn);
			return {
				filters: {
					'project': d.project
				}
			};
		});

		me.frm.set_query("purchase_invoice", "expenses", function(doc, cdt, cdn) {
			var d = frappe.get_doc(cdt, cdn);
			if (!d.requires_purchase_invoice) {
				return {
					filters: {
						name: ""
					}
				}
			} else {
				return {
					filters: {
						company: me.frm.doc.company,
						outstanding_amount: ['>', 0],
						docstatus: 1
					}
				};
			}
		});

		me.frm.set_query("party_type", "expenses", function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];

			return {
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
				filters: {
					'account': row.expense_account
				}
			}
		});
	}

	onload() {
		var me = this;
		if (me.frm.doc.docstatus == 0) {
			return frappe.call({
				method: "erpnext.hr.doctype.leave_application.leave_application.get_mandatory_approval",
				args: {
					doctype: me.frm.doc.doctype,
				},
				callback: function(r) {
					if (!r.exc && r.message) {
						me.frm.toggle_reqd("expense_approver", true);
					}
				}
			});
		}
	}

	refresh() {
		var me = this;

		erpnext.hide_company();
		erpnext.toggle_naming_series();

		if(me.frm.doc.docstatus === 1) {
			me.frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					company: me.frm.doc.company,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date,
					merge_similar_entries: 0
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));

			if (flt(me.frm.doc.outstanding_amount) > 0 && frappe.model.can_create("Payment Entry")) {
				me.frm.add_custom_button(__('Payment'), function() {
					me.make_payment_entry();
				}, __("Make"));
			}
		}

		if (!me.frm.doc.__islocal && me.frm.doc.docstatus==1) {
			me.frm.page.set_inner_btn_group_as_primary(__("Make"));
		}

		this.set_help();
	}

	calculate_totals() {
		var me = this;

		me.frm.doc.total_claimed_amount = 0;
		me.frm.doc.total_sanctioned_amount = 0;
		me.frm.doc.total_advance = 0;
		me.frm.doc.total_amount_reimbursed = 0;

		$.each(me.frm.doc.expenses || [], function(i, d) {
			frappe.model.round_floats_in(d, ['claim_amount', 'sanctioned_amount']);
			me.frm.doc.total_claimed_amount += d.claim_amount;
			me.frm.doc.total_sanctioned_amount += d.sanctioned_amount;
		});
		$.each(me.frm.doc.advances || [], function(i, d) {
			frappe.model.round_floats_in(d, ['allocated_amount']);
			me.frm.doc.total_advance += d.allocated_amount;
		});

		frappe.model.round_floats_in(me.frm.doc, ["total_claimed_amount", "total_sanctioned_amount", "total_advance",
			"total_amount_reimbursed"]);
		me.frm.doc.outstanding_amount = flt(me.frm.doc.total_sanctioned_amount - me.frm.doc.total_amount_reimbursed - me.frm.doc.total_advance,
			precision("outstanding_amount"));

		me.frm.refresh_fields();
	}

	expense_type(doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(!doc.company) {
			d.expense_type = "";
			frappe.msgprint(__("Please set the Company"));
			this.frm.refresh_fields();
			return;
		}

		if(!d.expense_type || cint(d.requires_purchase_invoice)) {
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
					frappe.model.set_value(cdt, cdn, 'expense_account', r.message);
				}
			}
		});
	}

	purchase_invoice(doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(!doc.company) {
			frappe.model.set_value(cdt, cdn, 'purchase_invoice', "");
			frappe.msgprint(__("Please set the Company first"));
			return;
		}

		if(!cint(d.requires_purchase_invoice)) {
			frappe.model.set_value(cdt, cdn, 'purchase_invoice', "");
		} else if (d.purchase_invoice) {
			return frappe.call({
				method: "erpnext.hr.doctype.expense_claim.expense_claim.get_purchase_invoice_details",
				args: {
					"purchase_invoice": d.purchase_invoice
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, 'expense_account', r.message.account);
						frappe.model.set_value(cdt, cdn, 'party_type', r.message.party_type);
						frappe.model.set_value(cdt, cdn, 'party', r.message.party);
						frappe.model.set_value(cdt, cdn, 'project', r.message.project);
					}
				}
			});
		}
	}

	employee() {
		this.get_advances();
	}

	payable_account() {
		this.get_advances();
	}

	claim_amount(doc, cdt, cdn) {
		var child = locals[cdt][cdn];
		child.sanctioned_amount = child.claim_amount;

		this.calculate_totals(doc, cdt, cdn);
	}

	sanctioned_amount(doc, cdt, cdn) {
		this.calculate_totals(doc, cdt, cdn);
	}

	allocated_amount(doc, cdt, cdn) {
		this.calculate_totals(doc, cdt, cdn);
	}

	advances_remove(doc, cdt, cdn) {
		this.calculate_totals(doc, cdt, cdn);
	}

	expenses_remove(doc, cdt, cdn) {
		this.calculate_totals(doc, cdt, cdn);
	}

	get_advances() {
		var me = this;
		return me.frm.call({
			method: "set_advances",
			doc: me.frm.doc,
			callback: function(r, rt) {
				refresh_field("advances");
				me.calculate_totals();
				me.frm.dirty();
			}
		})
	}

	make_payment_entry() {
		var me = this;

		var method = "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry";
		if(me.frm.doc.__onload && me.frm.doc.__onload.make_payment_via_journal_entry) {
			method = "erpnext.hr.doctype.expense_claim.expense_claim.make_bank_entry";
		}
		return frappe.call({
			method: method,
			args: {
				"dt": me.frm.doc.doctype,
				"dn": me.frm.doc.name
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}

	set_help() {
		this.frm.set_intro("");
		if(this.frm.doc.__islocal && !in_list(frappe.user_roles, "HR User")) {
			this.frm.set_intro(__("Fill the form and save it"));
		}
	}
};

extend_cscript(cur_frm.cscript, new erpnext.hr.ExpenseClaimController({frm: cur_frm}));
