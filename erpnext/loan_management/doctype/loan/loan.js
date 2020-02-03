// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/loan_management/loan_common.js' %};

frappe.ui.form.on('Loan', {
	setup: function(frm) {
		frm.make_methods = {
			'Loan Disbursement': function() { frm.trigger('make_loan_disbursement') },
			'Loan Security Unpledge': function() { frm.trigger('create_loan_security_unpledge') }
		}
	},
	onload: function (frm) {
		frm.set_query("loan_application", function () {
			return {
				"filters": {
					"applicant": frm.doc.applicant,
					"docstatus": 1,
					"status": "Approved"
				}
			};
		});

		$.each(["penalty_income_account", "interest_income_account"], function(i, field) {
			frm.set_query(field, function () {
				return {
					"filters": {
						"company": frm.doc.company,
						"root_type": "Income",
						"is_group": 0
					}
				};
			});
		});

		$.each(["payment_account", "loan_account"], function (i, field) {
			frm.set_query(field, function () {
				return {
					"filters": {
						"company": frm.doc.company,
						"root_type": "Asset",
						"is_group": 0
					}
				};
			});
		})

		frm.set_query('loan_security_pledge', function(doc, cdt, cdn) {
			return {
				filters: {
					applicant: frm.doc.applicant,
					docstatus: 1,
					loan_application: frm.doc.loan_application || ''
				}
			};
		});
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1) {
			if (frm.doc.status == "Sanctioned" || frm.doc.status == 'Partially Disbursed') {
				frm.add_custom_button(__('Loan Disbursement'), function() {
					frm.trigger("make_loan_disbursement");
				},__('Create'));
			} 
			
			if (["Disbursed", "Partially Disbursed"].includes(frm.doc.status) && (!frm.doc.repay_from_salary)) {
				frm.add_custom_button(__('Loan Repayment'), function() {
					frm.trigger("make_repayment_entry");
				},__('Create'));

			}

			if (frm.doc.status == "Loan Closure Requested") {
				frm.add_custom_button(__('Loan Security Unpledge'), function() {
					frm.trigger("create_loan_security_unpledge");
				},__('Create'));
			}
		}
		frm.trigger("toggle_fields");
	},

	loan_type: function(frm) {
		frm.set_df_property("repayment_method", 'reqd', frm.doc.is_term_loan);
		frm.set_df_property("repayment_method", 'hidden', 1 - frm.doc.is_term_loan);
		frm.set_df_property("repayment_periods", 'hidden', 1 - frm.doc.is_term_loan);
	},

	is_secured_loan: function(frm) {
		frm.set_df_property("loan_security_pledge", 'reqd', frm.doc.is_secured_loan);
	},

	make_loan_disbursement: function (frm) {
		frappe.call({
			args: {
				"loan": frm.doc.name,
				"loan_amount": frm.doc.loan_amount,
				"company": frm.doc.company,
				"applicant_type": frm.doc.applicant_type,
				"applicant": frm.doc.applicant,
				"disbursed_amount": frm.doc.disbursed_amount
			},
			method: "erpnext.loan_management.doctype.loan.loan.make_loan_disbursement",
			callback: function (r) {
				if (r.message)
					var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		})
	},

	make_repayment_entry: function(frm) {
		frappe.call({
			args: {
				"loan": frm.doc.name,
				"applicant_type": frm.doc.applicant_type,
				"applicant": frm.doc.applicant,
				"loan_type": frm.doc.loan_type,
				"company": frm.doc.company
			},
			method: "erpnext.loan_management.doctype.loan.loan.make_repayment_entry",
			callback: function (r) {
				if (r.message)
					var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		})
	},

	create_loan_security_unpledge: function(frm) {
		frappe.call({
			method: "erpnext.loan_management.doctype.loan.loan.create_loan_security_unpledge",
			args : {
				"loan": frm.doc.name,
				"applicant_type": frm.doc.applicant_type,
				"applicant": frm.doc.applicant,
				"company": frm.doc.company
			},
			callback: function(r) {
				if (r.message)
					var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		})
	},

	loan_application: function (frm) {
		if(frm.doc.loan_application){
			return frappe.call({
				method: "erpnext.loan_management.doctype.loan.loan.get_loan_application",
				args: {
                    "loan_application": frm.doc.loan_application
                },
                callback: function (r) {
                    if (!r.exc && r.message) {
                        frm.set_value("loan_type", r.message.loan_type);
                        frm.set_value("loan_amount", r.message.loan_amount);
                        frm.set_value("repayment_method", r.message.repayment_method);
                        frm.set_value("monthly_repayment_amount", r.message.repayment_amount);
                        frm.set_value("repayment_periods", r.message.repayment_periods);
						frm.set_value("rate_of_interest", r.message.rate_of_interest);
						frm.set_value("is_secured_loan", r.message.is_secured_loan);

						if (frm.doc.is_secured_loan) {
							$.each(r.message.proposed_pledges, function(i, d) {
								let row = frm.add_child("securities");
								row.loan_security = d.loan_security;
								row.qty = d.qty;
								row.loan_security_price = d.loan_security_price;
								row.amount = d.amount;
								row.haircut = d.haircut;
							});

							frm.refresh_fields("securities");
						}
                    }
                }
            });
        }
	},

	repayment_method: function (frm) {
		frm.trigger("toggle_fields")
	},

	toggle_fields: function (frm) {
		frm.toggle_enable("monthly_repayment_amount", frm.doc.repayment_method == "Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method == "Repay Over Number of Periods")
	}
});
