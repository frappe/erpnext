// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('time_sheet', 'total_hours', 'working_hours');

frappe.ui.form.on("Salary Slip", {
	setup: function(frm) {
		frm.fields_dict["timesheets"].grid.get_field("time_sheet").get_query = function(){
			return {
				filters: {
					employee: frm.doc.employee
				}
			}
		}
		frm.set_query("salary_component", "earnings", function() {
			return {
				filters: {
					type: "earning"
				}
			}
		})
		frm.set_query("salary_component", "deductions", function() {
			return {
				filters: {
					type: "deduction"
				}
			}
		})
	},

	company: function(frm) {
		var company = locals[':Company'][frm.doc.company];
		if(!frm.doc.letter_head && company.default_letter_head) {
			frm.set_value('letter_head', company.default_letter_head);
		}
	},

	refresh: function(frm) {
		frm.trigger("toggle_fields")
		frm.trigger("toggle_reqd_fields")
		var salary_detail_fields = ['formula', 'abbr', 'statistical_component']
		cur_frm.fields_dict['earnings'].grid.set_column_disp(salary_detail_fields,false);
		cur_frm.fields_dict['deductions'].grid.set_column_disp(salary_detail_fields,false);
	},	

	salary_slip_based_on_timesheet: function(frm) {
		frm.trigger("toggle_fields")
	},
	
	payroll_frequency: function(frm) {
		frm.trigger("toggle_fields")
	},

	toggle_fields: function(frm) {
		frm.toggle_display(['hourly_wages', 'timesheets'],
			cint(frm.doc.salary_slip_based_on_timesheet)==1);

		frm.toggle_display(['payment_days', 'total_working_days', 'leave_without_pay'],
			frm.doc.payroll_frequency!="");
	}
	
})

frappe.ui.form.on('Salary Detail', {
	earnings_remove: function(frm, dt, dn) {
		calculate_all(frm.doc, dt, dn);
	},
	deductions_remove: function(frm, dt, dn) {
		calculate_all(frm.doc, dt, dn);
	}
})

// Get leave details
//---------------------------------------------------------------------
cur_frm.cscript.start_date = function(doc, dt, dn){
	return frappe.call({
		method: 'get_emp_and_leave_details',
		doc: locals[dt][dn],
		callback: function(r, rt) {
			cur_frm.refresh();
			calculate_all(doc, dt, dn);
		}
	});
}

cur_frm.cscript.payroll_frequency = cur_frm.cscript.salary_slip_based_on_timesheet = cur_frm.cscript.start_date;
cur_frm.cscript.end_date = cur_frm.cscript.start_date;

cur_frm.cscript.employee = function(doc,dt,dn){
	doc.salary_structure = ''
	cur_frm.cscript.start_date(doc, dt, dn)
}

cur_frm.cscript.leave_without_pay = function(doc,dt,dn){
	if (doc.employee && doc.start_date && doc.end_date) {
		return $c_obj(doc, 'get_leave_details', {"lwp": doc.leave_without_pay}, function(r, rt) {
			var doc = locals[dt][dn];
			cur_frm.refresh();
			calculate_all(doc, dt, dn);
		});
	}
}

var calculate_all = function(doc, dt, dn) {
	calculate_earning_total(doc, dt, dn);
	calculate_ded_total(doc, dt, dn);
	calculate_net_pay(doc, dt, dn);
}

cur_frm.cscript.amount = function(doc,dt,dn){
	var child = locals[dt][dn];
	if(!doc.salary_structure){
		frappe.model.set_value(dt,dn, "default_amount", child.amount)
	}
	calculate_all(doc, dt, dn);
}

cur_frm.cscript.depends_on_lwp = function(doc,dt,dn){
	calculate_earning_total(doc, dt, dn, true);
	calculate_ded_total(doc, dt, dn, true);
	calculate_net_pay(doc, dt, dn);
	refresh_many(['amount','gross_pay', 'rounded_total', 'net_pay', 'loan_repayment']);
};

// Calculate earning total
// ------------------------------------------------------------------------
var calculate_earning_total = function(doc, dt, dn, reset_amount) {
	var tbl = doc.earnings || [];
	var total_earn = 0;
	for(var i = 0; i < tbl.length; i++){
		if(cint(tbl[i].depends_on_lwp) == 1) {
			tbl[i].amount =  Math.round(tbl[i].default_amount)*(flt(doc.payment_days) /
				cint(doc.total_working_days)*100)/100;
			refresh_field('amount', tbl[i].name, 'earnings');
		} else if(reset_amount) {
			tbl[i].amount = tbl[i].default_amount;
			refresh_field('amount', tbl[i].name, 'earnings');
		}
		total_earn += flt(tbl[i].amount);
	}
	doc.gross_pay = total_earn;
	refresh_many(['amount','gross_pay']);
}

// Calculate deduction total
// ------------------------------------------------------------------------
var calculate_ded_total = function(doc, dt, dn, reset_amount) {
	var tbl = doc.deductions || [];
	var total_ded = 0;
	for(var i = 0; i < tbl.length; i++){
		if(cint(tbl[i].depends_on_lwp) == 1) {
			tbl[i].amount = Math.round(tbl[i].default_amount)*(flt(doc.payment_days)/cint(doc.total_working_days)*100)/100;
			refresh_field('amount', tbl[i].name, 'deductions');
		} else if(reset_amount) {
			tbl[i].amount = tbl[i].default_amount;
			refresh_field('amount', tbl[i].name, 'deductions');
		}
		total_ded += flt(tbl[i].amount);
	}
	doc.total_deduction = total_ded;
	refresh_field('total_deduction');
}

// Calculate net payable amount
// ------------------------------------------------------------------------
var calculate_net_pay = function(doc, dt, dn) {
	doc.net_pay = flt(doc.gross_pay) - flt(doc.total_deduction);
	doc.rounded_total = Math.round(doc.net_pay);
	refresh_many(['net_pay', 'rounded_total']);
}

// validate
// ------------------------------------------------------------------------
cur_frm.cscript.validate = function(doc, dt, dn) {
	calculate_all(doc, dt, dn);
}

cur_frm.fields_dict.employee.get_query = function(doc,cdt,cdn) {
	return{
		query: "erpnext.controllers.queries.employee_query"
	}
}
