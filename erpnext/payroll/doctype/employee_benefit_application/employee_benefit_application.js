// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Benefit Application', {
	employee: function(frm) {
		if (frm.doc.employee) {
			frappe.run_serially([
				() => 	frm.trigger('get_employee_currency'),
				() => 	frm.trigger('set_earning_component')
			]);
		}
		var method, args;
		if(frm.doc.employee && frm.doc.date && frm.doc.payroll_period){
			method = "erpnext.payroll.doctype.employee_benefit_application.employee_benefit_application.get_max_benefits_remaining";
			args = {
				employee: frm.doc.employee,
				on_date: frm.doc.date,
				payroll_period: frm.doc.payroll_period
			};
			get_max_benefits(frm, method, args);
		}
		else if(frm.doc.employee && frm.doc.date){
			method = "erpnext.payroll.doctype.employee_benefit_application.employee_benefit_application.get_max_benefits";
			args = {
				employee: frm.doc.employee,
				on_date: frm.doc.date
			};
			get_max_benefits(frm, method, args);
		}
	},

	date: function(frm) {
		frm.trigger('set_earning_component');
	},

	set_earning_component: function(frm) {
		if(!frm.doc.employee && !frm.doc.date) return;
		frm.set_query("earning_component", "employee_benefits", function() {
			return {
				query : "erpnext.payroll.doctype.employee_benefit_application.employee_benefit_application.get_earning_components",
				filters: {date: frm.doc.date, employee: frm.doc.employee}
			};
		});
	},

	get_employee_currency: function(frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: "erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment.get_employee_currency",
				args: {
					employee: frm.doc.employee,
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('currency', r.message);
						frm.refresh_fields();
					}
				}
			});
		}
	},

	payroll_period: function(frm) {
		var method, args;
		if (frm.doc.employee && frm.doc.date && frm.doc.payroll_period) {
			method = "erpnext.payroll.doctype.employee_benefit_application.employee_benefit_application.get_max_benefits_remaining";
			args = {
				employee: frm.doc.employee,
				on_date: frm.doc.date,
				payroll_period: frm.doc.payroll_period
			};
			get_max_benefits(frm, method, args);
		}
	},
	max_benefits: function(frm) {
		calculate_all(frm.doc);
	}
});

var get_max_benefits=function(frm, method, args) {
	frappe.call({
		method: method,
		args: args,
		callback: function (data) {
			if (!data.exc) {
				if (data.message) {
					frm.set_value("max_benefits", data.message);
				} else {
					frm.set_value("max_benefits", 0);
				}
			}
			frm.refresh_fields();
		}
	});
};

frappe.ui.form.on("Employee Benefit Application Detail",{
	amount:  function(frm) {
		calculate_all(frm.doc);
	},
	employee_benefits_remove: function(frm) {
		calculate_all(frm.doc);
	}
});

var calculate_all = function(doc) {
	var tbl = doc.employee_benefits || [];
	var pro_rata_dispensed_amount = 0;
	var total_amount = 0;
	if (doc.max_benefits === 0) {
		doc.employee_benefits = [];
	} else {
		for (var i = 0; i < tbl.length; i++) {
			if (cint(tbl[i].amount) > 0) {
				total_amount += flt(tbl[i].amount);
			}
			if (tbl[i].pay_against_benefit_claim != 1) {
				pro_rata_dispensed_amount += flt(tbl[i].amount);
			}
		}
	}

	doc.total_amount = total_amount;
	doc.remaining_benefit = doc.max_benefits - total_amount;
	doc.pro_rata_dispensed_amount = pro_rata_dispensed_amount;
	refresh_many(['pro_rata_dispensed_amount', 'total_amount','remaining_benefit']);
};
