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
		if (frm.doc.docstatus == 1 && frm.doc.status == "Sanctioned") {
			frm.add_custom_button(__('Create Disbursement Entry'), function() {
				frm.trigger("make_jv");
			})
		}
		if (frm.doc.repayment_schedule) {
			let total_amount_paid = 0;
			$.each(frm.doc.repayment_schedule || [], function(i, row) {
				if (row.paid) {
					total_amount_paid += row.total_payment;
				}
			});
			frm.set_value("total_amount_paid", total_amount_paid);
;		}
		if (frm.doc.docstatus == 1 && frm.doc.repayment_start_date && (frm.doc.applicant_type == 'Member' || frm.doc.repay_from_salary == 0)) {
			frm.add_custom_button(__('Create Repayment Entry'), function() {
				frm.trigger("make_repayment_entry");
			})
		}
		frm.trigger("toggle_fields");
	},
	status: function (frm) {
		frm.toggle_reqd("disbursement_date", frm.doc.status == 'Disbursed')
		frm.toggle_reqd("repayment_start_date", frm.doc.status == 'Disbursed')
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
				"payment_account": frm.doc.payment_account
			},
			method: "erpnext.hr.doctype.loan.loan.make_jv_entry",
			callback: function (r) {
				if (r.message)
					var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		})
	},
	make_repayment_entry: function(frm) {
		var repayment_schedule = $.map(frm.doc.repayment_schedule, function(d) { return d.paid ? d.payment_date : false; });
		if(repayment_schedule.length >= 1){
			frm.repayment_data = [];
			frm.show_dialog = 1;
			let title = "";
			let fields = [
			{fieldtype:'Section Break', label: __('Repayment Schedule')},
			{fieldname: 'payments', fieldtype: 'Table',
				fields: [
					{
						fieldtype:'Data',
						fieldname:'payment_date',
						label: __('Date'),
						read_only:1,
						in_list_view: 1,
						columns: 2
					},
					{
						fieldtype:'Currency',
						fieldname:'principal_amount',
						label: __('Principal Amount'),
						read_only:1,
						in_list_view: 1,
						columns: 3
					},
					{
						fieldtype:'Currency',
						fieldname:'interest_amount',
						label: __('Interest'),
						read_only:1,
						in_list_view: 1,
						columns: 2
					},
					{
						fieldtype:'Currency',
						read_only:1,
						fieldname:'total_payment',
						label: __('Total Payment'),
						in_list_view: 1,
						columns: 3
					},
				],
				data: frm.repayment_data,
				get_data: function() {
					return frm.repayment_data;
				}
			}
		]

		var dialog = new frappe.ui.Dialog({
			title: title, fields: fields,
		});
		if (frm.doc['repayment_schedule']) {
			frm.doc['repayment_schedule'].forEach((payment, index) => {
			if (payment.paid == 0 && payment.payment_date <= frappe.datetime.now_date()) {
					frm.repayment_data.push ({
						'id': index,
						'name': payment.name,
						'payment_date': payment.payment_date,
						'principal_amount': payment.principal_amount,
						'interest_amount': payment.interest_amount,
						'total_payment': payment.total_payment
					});
					dialog.fields_dict.payments.grid.refresh();
					$(dialog.wrapper.find(".grid-buttons")).hide();
					$(`.octicon.octicon-triangle-down`).hide();
				}

			})
		}

		dialog.show()
		dialog.set_primary_action(__('Create Repayment Entry'), function() {
			frm.values = dialog.get_values();
			if(frm.values) {
				_make_repayment_entry(frm, dialog.fields_dict.payments.grid.get_selected_children());
				dialog.hide()
				}
			});
		}

		dialog.get_close_btn().on('click', () => {
			dialog.hide();
		});
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

var _make_repayment_entry = function(frm, payment_rows) {
	frappe.call({
		method:"erpnext.hr.doctype.loan.loan.make_repayment_entry",
		args: {
			payment_rows: payment_rows,
			"loan": frm.doc.name,
			"company": frm.doc.company,
			"loan_account": frm.doc.loan_account,
			"applicant_type": frm.doc.applicant_type,
			"applicant": frm.doc.applicant,
			"payment_account": frm.doc.payment_account,
			"interest_income_account": frm.doc.interest_income_account
		},
		callback: function(r) {
			if (r.message)
				var doc = frappe.model.sync(r.message)[0];
			frappe.set_route("Form", doc.doctype, doc.name, {'payment_rows': payment_rows});
		}
	});
}