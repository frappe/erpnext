// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/hr/loan_common.js' %};

frappe.ui.form.on('Loan', {
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

		frm.set_query("interest_income_account", function () {
			return {
				"filters": {
					"company": frm.doc.company,
					"root_type": "Income",
					"is_group": 0
				}
			};
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
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1 && (frm.doc.status == "Sanctioned" || frm.doc.status == "Partially Disbursed")) {
			frm.add_custom_button(__('Make Disbursement Entry'), function() {
				frm.trigger("make_jv");
			})
		}
		if (frm.doc.docstatus == 1 && (frm.doc.applicant_type == 'Member' || frm.doc.repay_from_salary == 0)) {
			frm.add_custom_button(__('Make Repayment Entry'), function() {
				frm.trigger("make_jv");
			})
		}
		frm.trigger("toggle_fields");
	},
	make_jv: function (frm) {
		frappe.call({
			args: {
				"loan": frm.doc.name,
				"company": frm.doc.company,
				"loan_account": frm.doc.loan_account,
				"applicant_type": frm.doc.applicant_type,
				"applicant": frm.doc.applicant,
				"loan_amount": frm.doc.loan_amount,
				"payment_account": frm.doc.payment_account,
				"interest_income_account": frm.doc.interest_income_account,
				"repay_from_salary": frm.doc.repay_from_salary
			},
			method: "erpnext.hr.doctype.loan.loan.make_jv_entry",
			callback: function (r) {
				if (r.message)
					var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		})
	},
	mode_of_payment: function (frm) {
		frappe.call({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
			args: {
				"mode_of_payment": frm.doc.mode_of_payment,
				"company": frm.doc.company
			},
			callback: function (r, rt) {
				if (r.message) {
					frm.set_value("payment_account", r.message.account);
				}
			}
		});
	},

	loan_application: function (frm) {
	    if(frm.doc.loan_application){
            return frappe.call({
                method: "erpnext.hr.doctype.loan.loan.get_loan_application",
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
