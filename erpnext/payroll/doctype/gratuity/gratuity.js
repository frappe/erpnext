// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gratuity', {
	setup: function (frm) {
		frm.set_query('salary_component', function () {
			return {
				filters: {
					type: "Earning"
				}
			};
		});
		frm.set_query("expense_account", function () {
			return {
				filters: {
					"root_type": "Expense",
					"is_group": 0,
					"company": frm.doc.company
				}
			};
		});

		frm.set_query("payable_account", function () {
			return {
				filters: {
					"root_type": "Liability",
					"is_group": 0,
					"company": frm.doc.company
				}
			};
		});
	},
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && frm.doc.pay_via_salary_slip === 0 && frm.doc.status === "Unpaid") {
			frm.add_custom_button(__("Create Payment Entry"), function () {
				return frappe.call({
					method: 'erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry',
					args: {
						"dt": frm.doc.doctype,
						"dn": frm.doc.name
					},
					callback: function (r) {
						var doclist = frappe.model.sync(r.message);
						frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
					}
				});
			});
		}
	},
	employee: function (frm) {
		frm.events.calculate_work_experience_and_amount(frm);
	},
	gratuity_rule: function (frm) {
		frm.events.calculate_work_experience_and_amount(frm);
	},
	calculate_work_experience_and_amount: function (frm) {

		if (frm.doc.employee && frm.doc.gratuity_rule) {
			frappe.call({
				method: "erpnext.payroll.doctype.gratuity.gratuity.calculate_work_experience_and_amount",
				args: {
					employee: frm.doc.employee,
					gratuity_rule: frm.doc.gratuity_rule
				}
			}).then((r) => {
				frm.set_value("current_work_experience", r.message['current_work_experience']);
				frm.set_value("amount", r.message['amount']);
			});
		}
	}

});