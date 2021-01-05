// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.hr");
frappe.provide("erpnext.accounts.dimensions");
frappe.provide("erpnext.accounts");
{% include 'erpnext/public/js/controllers/buying.js' %};

erpnext.hr.ExpenseClaimController = erpnext.buying.BuyingController.extend({
	item_code: function(doc, cdt, cdn) {
		this._super(doc, cdt, cdn);
		let d = locals[cdt][cdn];
		if (!doc.company) {
			d.item_code = "";
			frappe.msgprint(__("Please set the Company"));
			this.frm.refresh_fields();
			return;
		}

		if (!d.item_code) {
			return;
		}
		return frappe.call({
			method: "erpnext.hr.doctype.expense_claim.expense_claim.get_expense_claim_account_and_cost_center",
			args: {
				"item_code": d.item_code,
				"company": doc.company
			},
			callback: function(r) {
				if (r.message) {
					d.default_account = r.message.account;
					d.cost_center = r.message.cost_center;
				}
			}
		});
	}
});

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee','employee_name','employee_name');
cur_frm.add_fetch('item_code','description','description');

cur_frm.cscript.onload = function(doc) {
	if (doc.__islocal) {
		cur_frm.set_value("posting_date", frappe.datetime.get_today());
		cur_frm.cscript.clear_sanctioned(doc);
	}
};

cur_frm.cscript.clear_sanctioned = function(doc) {
	var val = doc.items || [];
	for(var i = 0; i<val.length; i++){
		val[i].amount ='';
	}

	doc.total = '';
	refresh_many(['amount', 'total']);
};

cur_frm.cscript.refresh = function(doc) {
	cur_frm.cscript.set_help(doc);

	if(!doc.__islocal) {

		if (doc.docstatus===1) {
			/* eslint-disable */
			// no idea how `me` works here
			var entry_doctype, entry_reference_doctype, entry_reference_name;
			if(doc.__onload.make_payment_via_journal_entry){
				entry_doctype = "Journal Entry";
				entry_reference_doctype = "Journal Entry Account.reference_type";
				entry_reference_name = "Journal Entry.reference_name";
			} else {
				entry_doctype = "Payment Entry";
				entry_reference_doctype = "Payment Entry Reference.reference_doctype";
				entry_reference_name = "Payment Entry Reference.reference_name";
			}

			if (cint(doc.total_amount_reimbursed) > 0 && frappe.model.can_read(entry_doctype)) {
				cur_frm.add_custom_button(__('Bank Entries'), function() {
					frappe.route_options = {
						party_type: "Employee",
						party: doc.employee,
						company: doc.company
					};
					frappe.set_route("List", entry_doctype);
				}, __("View"));
			}
			/* eslint-enable */
		}
	}
};

cur_frm.cscript.set_help = function(doc) {
	cur_frm.set_intro("");
	if(doc.__islocal && !in_list(frappe.user_roles, "HR User")) {
		cur_frm.set_intro(__("Fill the form and save it"));
	}
};

cur_frm.cscript.validate = function(doc) {
	cur_frm.cscript.calculate_total(doc);
};

cur_frm.cscript.calculate_total = function(doc){
	doc.total_claimed_amount = 0;
	$.each((doc.items || []), function(i, d) {
		doc.total_claimed_amount += d.claimed_amount;
	});
	this.set_in_company_currency(this.frm.doc, ["total_claimed_amount"])
};

cur_frm.cscript.calculate_total_amount = function(doc,cdt,cdn){
	cur_frm.cscript.calculate_total(doc,cdt,cdn);
};

cur_frm.fields_dict['cost_center'].get_query = function(doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};

erpnext.expense_claim = {
	set_title: function(frm) {
		if (!frm.doc.task) {
			frm.set_value("title", frm.doc.employee_name);
		}
		else {
			frm.set_value("title", frm.doc.employee_name + " for "+ frm.doc.task);
		}
	}
};

frappe.ui.form.on("Expense Claim", {
	setup: function(frm) {
		frm.add_fetch("company", "cost_center", "cost_center");
		frm.add_fetch("company", "default_expense_claim_payable_account", "payable_account");

		frm.set_query("employee_advance", "advances", function() {
			return {
				filters: [
					['docstatus', '=', 1],
					['employee', '=', frm.doc.employee],
					['paid_amount', '>', 0],
					['paid_amount', '>', 'claimed_amount']
				]
			};
		});

		frm.set_query("item_code", "items", function() {
			return {
				filters: {
					"disabled": 0,
					"is_stock_item": 0
				}
			}
		});

		frm.set_query("expense_approver", function() {
			return {
				query: "erpnext.hr.doctype.department_approver.department_approver.get_approvers",
				filters: {
					employee: frm.doc.employee,
					doctype: frm.doc.doctype
				}
			};
		});

		frm.set_query("account_head", "taxes", function() {
			return {
				filters: [
					['company', '=', frm.doc.company],
					['account_type', 'in', ["Tax", "Chargeable", "Income Account", "Expenses Included In Valuation"]]
				]
			};
		});

<<<<<<< HEAD
=======
		frm.set_query("cost_center", "items", function() {
			return {
				filters: {
					"company": frm.doc.company,
					"is_group": 0
				}
			};
		});

>>>>>>> refactor: replace Expense Taxes and Charges with Purchase Taxes table
		frm.set_query("payable_account", function() {
			return {
				filters: {
					"report_type": "Balance Sheet",
					"account_type": "Payable",
					"company": frm.doc.company,
					"is_group": 0
				}
			};
		});

		frm.set_query("task", function() {
			return {
				filters: {
					'project': frm.doc.project
				}
			};
		});

		frm.set_query("employee", function() {
			return {
				query: "erpnext.controllers.queries.employee_query"
			};
		});
	},

	onload: function(frm) {
		if (frm.doc.docstatus == 0) {
			return frappe.call({
				method: "erpnext.hr.doctype.leave_application.leave_application.get_mandatory_approval",
				args: {
					doctype: frm.doc.doctype,
				},
				callback: function(r) {
					if (!r.exc && r.message) {
						frm.toggle_reqd("expense_approver", true);
					}
				}
			});
		}
	},

	refresh: function(frm) {
		frm.trigger("toggle_fields");
		frm.events.set_dynamic_currency_labels(frm);
		frm.events.toggle_currency_fields(frm);

		if(frm.doc.docstatus > 0 && frm.doc.approval_status !== "Rejected") {
			frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					company: frm.doc.company,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
					group_by: '',
					show_cancelled_entries: frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}

		if (frm.doc.docstatus===1 && !cint(frm.doc.is_paid) && cint(frm.doc.grand_total) > 0
				&& (cint(frm.doc.total_amount_reimbursed) < cint(frm.doc.total))
				&& frappe.model.can_create("Payment Entry")) {
			frm.add_custom_button(__('Payment'),
				function() { frm.events.make_payment_entry(frm); }, __('Create'));
		}
	},

	calculate_grand_total_and_outstanding_amount: function(frm) {
		let grand_total = flt(frm.doc.total) + flt(frm.doc.total_taxes_and_charges);
		frm.set_value("grand_total", grand_total);

		let outstanding_amount = flt(frm.doc.grand_total) - flt(frm.doc.total_advance_amount) - flt(frm.doc.total_amount_reimbursed);
		frm.set_value("outstanding_amount", outstanding_amount);
		frm.refresh_fields();
	},

	calculate_total_advance: function(frm) {
		let total_advance_amount = 0;
		$.each(frm.doc.advances, (_i, d) => {
			total_advance_amount += flt(d.allocated_amount);
		})

		frm.set_value("total_advance_amount", total_advance_amount);
	},

	grand_total: function(frm) {
		frm.trigger("update_employee_advance_claimed_amount");
	},

	update_employee_advance_claimed_amount: function(frm) {
		let amount_to_be_allocated = frm.doc.grand_total;
		$.each(frm.doc.advances || [], function(i, advance){
			if (amount_to_be_allocated >= advance.unclaimed_amount){
				advance.allocated_amount = frm.doc.advances[i].unclaimed_amount;
				amount_to_be_allocated -= advance.allocated_amount;
			} else {
				advance.allocated_amount = amount_to_be_allocated;
				amount_to_be_allocated = 0;
			}
			frm.refresh_field("advances");
		});
	},

	make_payment_entry: function(frm) {
		var method = "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry";
		if(frm.doc.__onload && frm.doc.__onload.make_payment_via_journal_entry) {
			method = "erpnext.hr.doctype.expense_claim.expense_claim.make_bank_entry";
		}
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

	is_paid: function(frm) {
		frm.trigger("toggle_fields");
	},

	toggle_fields: function(frm) {
		frm.toggle_reqd("mode_of_payment", frm.doc.is_paid);
	},

	employee_name: function(frm) {
		erpnext.expense_claim.set_title(frm);
	},

	task: function(frm) {
		erpnext.expense_claim.set_title(frm);
	},

	employee: function(frm) {
		if (frm.doc.employee) {
			frappe.run_serially([
				() => 	frm.trigger("get_employee_currency"),
				() => 	frm.trigger("get_employee_advances")
			]);
		}
	},

	get_employee_currency: function(frm) {
		frappe.call({
			method: "erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment.get_employee_currency",
			args: {
				employee: frm.doc.employee,
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value("currency", r.message);
					frm.refresh_fields();
				}
			}
		});
	},

	currency: function(frm) {
		let from_currency = frm.doc.currency;
		let company_currency;
		if (!frm.doc.company) {
			company_currency = erpnext.get_currency(frappe.defaults.get_default("Company"));
		} else {
			company_currency = erpnext.get_currency(frm.doc.company);
		}

		if (from_currency != company_currency) {
			frm.events.set_exchange_rate(frm, from_currency, company_currency);
			frm.events.set_dynamic_currency_labels(frm);
			frm.events.toggle_currency_fields(frm);
		} else {
			frm.set_value("conversion_rate", 1.0);
			frm.set_df_property("conversion_rate", "hidden", 1);
			frm.set_df_property("conversion_rate", "description", "" );
		}
		frm.refresh_fields();
	},

	set_exchange_rate: function(frm, from_currency, company_currency) {
		frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				from_currency: from_currency,
				to_currency: company_currency,
			},
			callback: function(r) {
				frm.set_value("conversion_rate", flt(r.message));
				frm.set_df_property("conversion_rate", "hidden", 0);
				frm.set_df_property("conversion_rate", "description", "1 " + frm.doc.currency
					+ " = [?] " + company_currency);
			}
		});
	},

	set_dynamic_currency_labels: function(frm) {
		let from_currency = frm.doc.currency;
		let company_currency;
		if (!frm.doc.company) {
			company_currency = erpnext.get_currency(frappe.defaults.get_default("Company"));
		} else {
			company_currency = erpnext.get_currency(frm.doc.company);
		}

		if (from_currency != company_currency) {
			frm.set_currency_labels(["base_total_claimed_amount", "base_total", "base_total_amount_reimbursed",
				"base_taxes_and_charges_added", "base_taxes_and_charges_deducted", "base_total_taxes_and_charges",
				"base_grand_total"], company_currency);

			frm.set_currency_labels(["total_claimed_amount", "total", "total_amount_reimbursed",
				"taxes_and_charges_added", "taxes_and_charges_deducted", "total_taxes_and_charges",
				"grand_total", "total_advance_amount", "outstanding_amount"], from_currency);
		}
	},

	toggle_currency_fields: function(frm) {
		let from_currency = frm.doc.currency;
		let company_currency;
		if (!frm.doc.company) {
			company_currency = erpnext.get_currency(frappe.defaults.get_default("Company"));
		} else {
			company_currency = erpnext.get_currency(frm.doc.company);
		}

		frm.toggle_display("base_total_claimed_amount", (from_currency != company_currency));
		frm.toggle_display("base_total_amount_reimbursed", (from_currency != company_currency));
		frm.refresh_fields();
	},

	cost_center: function(frm) {
		frm.events.set_child_cost_center(frm);
	},

	validate: function(frm) {
		frm.events.set_child_cost_center(frm);
	},

	set_child_cost_center: function(frm){
		(frm.doc.items || []).forEach(function(d) {
			if (!d.cost_center){
				d.cost_center = frm.doc.cost_center;
			}
		});
	},

	get_employee_advances: function(frm) {
		frappe.model.clear_table(frm.doc, "advances");
		if (frm.doc.employee) {
			return frappe.call({
				method: "erpnext.hr.doctype.expense_claim.expense_claim.get_advances",
				args: {
					employee: frm.doc.employee
				},
				callback: function(r, rt) {

					if(r.message) {
						$.each(r.message, function(i, d) {
							let row = frappe.model.add_child(frm.doc, "Expense Claim Advance", "advances");
							row.employee_advance = d.name;
							row.posting_date = d.posting_date;
							row.advance_account = d.advance_account;
							row.advance_paid = d.paid_amount;
							row.unclaimed_amount = flt(d.paid_amount) - flt(d.claimed_amount);
							row.allocated_amount = 0;
						});
						refresh_field("advances");
						frm.trigger("calculate_total_advance");
					}
				}
			});
		}
	}
});

frappe.ui.form.on("Expense Claim Item", {
	claimed_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "rate", child.claimed_amount);
		frappe.model.set_value(cdt, cdn, "amount", child.claimed_amount);
	},

	amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "rate", child.amount);
		cur_frm.cscript.calculate_total(frm.doc, cdt, cdn);
	},

	cost_center: function(frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "cost_center");
	}
});

frappe.ui.form.on("Expense Claim Advance", {
	employee_advance: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(!frm.doc.employee){
			frappe.msgprint(__('Select an employee to get the employee advance.'));
			frm.doc.advances = [];
			refresh_field("advances");
		}
		else {
			return frappe.call({
				method: "erpnext.hr.doctype.expense_claim.expense_claim.get_advances",
				args: {
					employee: frm.doc.employee,
					advance_id: child.employee_advance
				},
				callback: function(r, rt) {
					if(r.message) {
						child.employee_advance = r.message[0].name;
						child.posting_date = r.message[0].posting_date;
						child.advance_account = r.message[0].advance_account;

						child.advance_paid = r.message[0].paid_amount;
						child.unclaimed_amount = flt(r.message[0].paid_amount) - flt(r.message[0].claimed_amount);
						child.allocated_amount = flt(r.message[0].paid_amount) - flt(r.message[0].claimed_amount);

						refresh_field("advances");
						frm.trigger("calculate_total_advance");
						frm.trigger("calculate_grand_total_and_outstanding_amount");
					}
				}
			});
		}
	}
});