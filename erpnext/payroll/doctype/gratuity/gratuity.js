// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gratuity', {
	refresh: function(frm){
		if(frm.doc.docstatus === 1 && frm.doc.pay_via_salary_slip === 0 && frm.doc.status === "Unpaid") {
			frm.add_custom_button(__("Make Payment Entry"), function() {
				frm.trigger('make_payment_entry');
			});
		}
	},
	onload: function(frm){
		frm.set_query('salary_component', function() {
			return {
				filters: {
					type: "Earning"
				}
			};
		});
	},
	employee: function(frm) {
		frm.events.calculate_work_experience_and_amount(frm);
	},
	gratuity_rule: function(frm){
		frm.events.calculate_work_experience_and_amount(frm);
	},
	calculate_work_experience_and_amount: function(frm) {

		if(frm.doc.employee && frm.doc.gratuity_rule){
			frappe.call({
				method:"erpnext.payroll.doctype.gratuity.gratuity.calculate_work_experience_and_amount",
				args:{
					employee: frm.doc.employee,
					gratuity_rule: frm.doc.gratuity_rule
				}
			}).then((r) => {
				frm.set_value("current_work_experience", r.message['current_work_experience']);
				frm.set_value("amount", r.message['amount']);
			});
		}
	},
	make_payment_entry: function(frm){
		console.log("Hello");
	}

});
