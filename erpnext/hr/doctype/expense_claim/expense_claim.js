// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.hr");
frappe.provide("erpnext.accounts.dimensions");
frappe.provide("erpnext.accounts");
{% include "erpnext/public/js/controllers/buying.js" %};

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

$.extend(cur_frm.cscript, new erpnext.hr.ExpenseClaimController({frm: cur_frm}));

cur_frm.cscript.refresh = function(doc) {
	if (!doc.__islocal) {

		if (doc.docstatus===1) {
			/* eslint-disable */
			// no idea how `me` works here
			let entry_doctype, entry_reference_doctype, entry_reference_name;
			if (doc.__onload.make_payment_via_journal_entry) {
				entry_doctype = "Journal Entry";
				entry_reference_doctype = "Journal Entry Account.reference_type";
				entry_reference_name = "Journal Entry.reference_name";
			} else {
				entry_doctype = "Payment Entry";
				entry_reference_doctype = "Payment Entry Reference.reference_doctype";
				entry_reference_name = "Payment Entry Reference.reference_name";
			}

			if (cint(doc.total_amount_reimbursed) > 0 && frappe.model.can_read(entry_doctype)) {
				cur_frm.add_custom_button(__("Bank Entries"), function() {
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

frappe.ui.form.on("Expense Claim", {
	refresh: function(frm) {
		frm.set_query("employee", function() {
			return {
				query: "erpnext.controllers.queries.employee_query"
			};
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

		frm.set_query("item_code", "items", function() {
			return {
				filters: {
					"disabled": 0,
					"is_stock_item": 0
				}
			}
		});

		frm.set_query("cost_center", "items", function() {
			return {
				filters: {
					"company": frm.doc.company,
					"is_group": 0
				}
			};
		});

		frm.set_query("employee_advance", "advances", function() {
			return {
				filters: [
					["docstatus", "=", 1],
					["employee", "=", frm.doc.employee],
					["paid_amount", ">", 0]
				]
			};
		});

		frm.set_query("account_head", "taxes", function() {
			return {
				filters: [
					["company", "=", frm.doc.company],
					["account_type", "in", ["Tax", "Chargeable", "Income Account", "Expenses Included In Valuation"]]
				]
			};
		});

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
					"project": frm.doc.project
				}
			};
		});

		frm.fields_dict.cost_center.get_query = function(doc) {
			return {
				filters: {
					"company": doc.company
				}
			}
		};

		frm.toggle_reqd("mode_of_payment", frm.doc.is_paid);
		frm.trigger("update_currency_fields");
		frm.trigger("setup_custom_buttons");
	},

	onload: function(frm) {
		if (frm.doc.__islocal) {
			frm.set_value("posting_date", frappe.datetime.get_today());
			frm.trigger("clear_sanctioned");
		}

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
		frm.trigger("update_currency_fields");
	},

	update_currency_fields: function(frm) {
		let from_currency = frm.doc.currency;
		let company_currency;
		if (!frm.doc.company) {
			company_currency = erpnext.get_currency(frappe.defaults.get_default("Company"));
		} else {
			company_currency = erpnext.get_currency(frm.doc.company);
		}

		if (from_currency != company_currency) {
			frm.events.set_exchange_rate(frm, from_currency, company_currency);
		} else {
			frm.set_value("conversion_rate", 1.0);
			frm.set_df_property("conversion_rate", "hidden", 1);
			frm.set_df_property("conversion_rate", "description", "" );
		}

		frm.events.set_dynamic_currency_labels(frm, from_currency, company_currency);
		frm.events.toggle_currency_fields(frm, from_currency, company_currency);
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

	set_dynamic_currency_labels: function(frm, from_currency, company_currency) {
		if (from_currency != company_currency) {
			frm.set_currency_labels(["base_total_claimed_amount", "base_total", "base_total_amount_reimbursed",
				"base_taxes_and_charges_added", "base_taxes_and_charges_deducted", "base_total_taxes_and_charges",
				"base_grand_total"], company_currency);

			frm.set_currency_labels(["total_claimed_amount", "total", "total_amount_reimbursed",
				"taxes_and_charges_added", "taxes_and_charges_deducted", "total_taxes_and_charges",
				"grand_total", "total_advance_amount", "outstanding_amount"], from_currency);
		}
	},

	toggle_currency_fields: function(frm, from_currency, company_currency) {
		frm.toggle_display("base_total_claimed_amount", (from_currency != company_currency));
		frm.toggle_display("base_total_amount_reimbursed", (from_currency != company_currency));
		frm.refresh_fields();
	},

	setup_custom_buttons: function(frm) {
		if (frm.doc.docstatus > 0 && frm.doc.approval_status !== "Rejected") {
			frm.add_custom_button(__("Accounting Ledger"), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					company: frm.doc.company,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
					group_by: "",
					show_cancelled_entries: frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}

		if (frm.doc.docstatus === 1 && !cint(frm.doc.is_paid) && cint(frm.doc.outstanding_amount) > 0
				&& frappe.model.can_create("Payment Entry")) {
			frm.add_custom_button(__("Payment"),
				function() { frm.events.make_payment_entry(frm); },
				 __("Create")
			);
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}
	},

	validate: function(frm) {
		frm.trigger("calculate_totals");
		frm.trigger("set_child_cost_center");
	},

	calculate_totals: function(frm) {
		let total_claimed_amount = 0;
		$.each((frm.doc.items || []), function(_i, d) {
			total_claimed_amount += flt(d.claimed_amount);
		});
		let base_total_claimed_amount = flt((flt(total_claimed_amount) * frm.doc.conversion_rate),
			precision("base_total_claimed_amount"));

		frm.set_value({
			"total_claimed_amount": total_claimed_amount,
			"base_total_claimed_amount": base_total_claimed_amount
		});
	},

	cost_center: function(frm) {
		frm.events.set_child_cost_center(frm);
	},

	set_child_cost_center: function(frm){
		(frm.doc.items || []).forEach(function(d) {
			if (!d.cost_center) {
				d.cost_center = frm.doc.cost_center;
			}
		});
	},

	clear_sanctioned: function(frm) {
		$.each((frm.doc.items || []), function(_i, d) {
			d.amount = "";
		});

		frm.doc.total = "";
		refresh_many(["amount", "total"]);
	},

	set_help: function(frm) {
		frm.set_intro("");
		if (frm.doc.__islocal && !in_list(frappe.user_roles, "HR User")) {
			frm.set_intro(__("Fill the form and save it"));
		}
	},

	update_employee_advance_claimed_amount: function(frm) {
		let amount_to_be_allocated = frm.doc.grand_total;
		$.each(frm.doc.advances || [], function(i, advance) {
			if (amount_to_be_allocated >= advance.unclaimed_amount) {
				advance.allocated_amount = frm.doc.advances[i].unclaimed_amount;
				amount_to_be_allocated -= advance.allocated_amount;
			} else {
				advance.allocated_amount = amount_to_be_allocated;
				amount_to_be_allocated = 0;
			}
		});

		frm.refresh_field("advances");
		frm.trigger("calculate_total_advance");
	},

	calculate_total_advance: function(frm) {
		let total_advance_amount = 0;
		$.each(frm.doc.advances, (_i, d) => {
			total_advance_amount += flt(d.allocated_amount);
		})

		frm.set_value("total_advance_amount", total_advance_amount);
		frm.trigger("calculate_outstanding_amount");
	},

	calculate_outstanding_amount: function(frm) {
		let outstanding_amount = flt(frm.doc.grand_total) - flt(frm.doc.total_advance_amount) - flt(frm.doc.total_amount_reimbursed);
		frm.set_value("outstanding_amount", outstanding_amount);
		frm.refresh_fields();
	},

	make_payment_entry: function(frm) {
		let method = "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry";
		if (frm.doc.__onload && frm.doc.__onload.make_payment_via_journal_entry) {
			method = "erpnext.hr.doctype.expense_claim.expense_claim.make_bank_entry";
		}
		return frappe.call({
			method: method,
			args: {
				"dt": frm.doc.doctype,
				"dn": frm.doc.name
			},
			callback: function(r) {
				let doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	is_paid: function(frm) {
		frm.toggle_reqd("mode_of_payment", frm.doc.is_paid);
	},

	employee_name: function(frm) {
		frm.trigger("set_title");
	},

	task: function(frm) {
		frm.trigger("set_title");
	},

	set_title: function(frm) {
		if (!frm.doc.task) {
			frm.set_value("title", frm.doc.employee_name);
		}
		else {
			frm.set_value("title", __("{0} for {1}", [frm.doc.employee_name, frm.doc.task]));
		}
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
		let child = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "rate", child.claimed_amount);
		frappe.model.set_value(cdt, cdn, "amount", child.claimed_amount);
	},

	amount: function(frm, cdt, cdn) {
		let child = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "rate", child.amount);
		frm.trigger("calculate_totals");
		frm.trigger("calculate_grand_total");
		frm.trigger("update_employee_advance_claimed_amount")
	},

	cost_center: function(frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "cost_center");
	}
});

frappe.ui.form.on("Expense Claim Advance", {
	employee_advance: function(frm, cdt, cdn) {
		let child = locals[cdt][cdn];
		if (!frm.doc.employee) {
			frappe.msgprint(__("Select an employee to get the employee advance."));
			frm.doc.advances = [];
			refresh_field("advances");
		} else {
			return frappe.call({
				method: "erpnext.hr.doctype.expense_claim.expense_claim.get_advances",
				args: {
					employee: frm.doc.employee,
					advance_id: child.employee_advance
				},
				callback: function(r, rt) {
					if (r.message) {
						child.employee_advance = r.message[0].name;
						child.posting_date = r.message[0].posting_date;
						child.advance_account = r.message[0].advance_account;

						child.advance_paid = r.message[0].paid_amount;
						child.unclaimed_amount = flt(r.message[0].paid_amount) - flt(r.message[0].claimed_amount);
						child.allocated_amount = flt(r.message[0].paid_amount) - flt(r.message[0].claimed_amount);

						refresh_field("advances");
						frm.trigger("calculate_total_advance");
					}
				}
			});
		}
	},

	allocated_amount: function(frm, cdt, cdn) {
		frm.trigger("calculate_total_advance");
	}
});