// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('time_sheet', 'total_hours', 'working_hours');

frappe.ui.form.on("Salary Slip", {
	setup: function(frm) {
		$.each(["earnings", "deductions"], function(i, table_fieldname) {
			frm.get_field(table_fieldname).grid.editable_fields = [
				{fieldname: 'salary_component', columns: 6},
				{fieldname: 'amount', columns: 4}
			];
		});

		frm.fields_dict["timesheets"].grid.get_field("time_sheet").get_query = function(){
			return {
				filters: {
					employee: frm.doc.employee
				}
			}
		};

		frm.set_query("salary_component", "earnings", function() {
			return {
				filters: {
					type: "earning"
				}
			}
		});

		frm.set_query("salary_component", "deductions", function() {
			return {
				filters: {
					type: "deduction"
				}
			}
		});

		frm.set_query("employee", function() {
			return{
				query: "erpnext.controllers.queries.employee_query"
			}
		});
	},

	start_date: function(frm){
		if(frm.doc.start_date){
			frm.trigger("set_end_date");
		}
	},

	end_date: function(frm) {
		frm.events.get_emp_and_working_day_details(frm);
	},

	set_end_date: function(frm){
		frappe.call({
			method: 'erpnext.payroll.doctype.payroll_entry.payroll_entry.get_end_date',
			args: {
				frequency: frm.doc.payroll_frequency,
				start_date: frm.doc.start_date
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value('end_date', r.message.end_date);
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

	currency: function(frm) {
		calculate_totals(frm.doc);
		frm.trigger("set_dynamic_labels")
		frm.refresh()
	},

	set_dynamic_labels: function(frm) {
		debugger;
		frm.set_currency_labels(["hour_rate", "gross_pay", "total_deduction", "net_pay", "rounded_total", "total_in_words"],
			frm.doc.currency);

		// toggle fields
		if(frappe.meta.get_docfield(cur_frm.doctype, "net_total"))
			cur_frm.toggle_display("net_total", show);

		frm.set_currency_labels(["amount", "default_amount", "additional_amount", "tax_on_flexible_benefit", "tax_on_additional_salary"],
			frm.doc.currency, "earnings");

		frm.set_currency_labels(["amount", "default_amount", "additional_amount", "tax_on_flexible_benefit", "tax_on_additional_salary"],
			frm.doc.currency, "deductions");

		frm.refresh_fields();
	},

	refresh: function(frm) {
		debugger;
		frm.trigger("set_dynamic_labels")
		frm.trigger("toggle_fields")

		var salary_detail_fields = ["formula", "abbr", "statistical_component", "variable_based_on_taxable_salary"];
		cur_frm.fields_dict['earnings'].grid.set_column_disp(salary_detail_fields,false);
		cur_frm.fields_dict['deductions'].grid.set_column_disp(salary_detail_fields,false);
		calculate_totals(frm.doc);
	},

	salary_slip_based_on_timesheet: function(frm) {
		frm.trigger("toggle_fields");
		frm.events.get_emp_and_working_day_details(frm);
	},

	payroll_frequency: function(frm) {
		frm.trigger("toggle_fields");
		frm.set_value('end_date', '');
	},

	employee: function(frm) {
		frm.events.get_emp_and_working_day_details(frm);
	},

	leave_without_pay: function(frm){
		if (frm.doc.employee && frm.doc.start_date && frm.doc.end_date) {
			return frappe.call({
				method: 'process_salary_based_on_working_days',
				doc: frm.doc,
				callback: function(r, rt) {
					frm.refresh();
				}
			});
		}
	},

	toggle_fields: function(frm) {
		frm.toggle_display(['hourly_wages', 'timesheets'], cint(frm.doc.salary_slip_based_on_timesheet)===1);

		frm.toggle_display(['payment_days', 'total_working_days', 'leave_without_pay'],
			frm.doc.payroll_frequency != "");
	},

	get_emp_and_working_day_details: function(frm) {
		debugger;
		return frappe.call({
			method: 'get_emp_and_working_day_details',
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh();
				if (r.message){
					frm.fields_dict.absent_days.set_description("Unmarked Days is treated as "+ r.message +". You can can change this in " + frappe.utils.get_form_link("Payroll Settings", "Payroll Settings", true));
				}
			}
		});
	}
});

frappe.ui.form.on('Salary Slip Timesheet', {
	time_sheet: function(frm, dt, dn) {
		total_work_hours(frm, dt, dn);
	},
	timesheets_remove: function(frm, dt, dn) {
		total_work_hours(frm, dt, dn);
	}
});


cur_frm.cscript.amount = function(doc, cdt, cdn){
	calculate_totals(doc, cdt, cdn);
};

// calculate total working hours, earnings based on hourly wages and totals
var total_work_hours = function(frm, dt, dn) {
	debugger;
	var total_working_hours = 0.0;
	$.each(frm.doc["timesheets"] || [], function(i, timesheet) {
		total_working_hours += timesheet.working_hours;
	});
	frm.set_value('total_working_hours', total_working_hours);

	var wages_amount = frm.doc.total_working_hours * frm.doc.hour_rate;

	frappe.db.get_value('Salary Structure', {'name': frm.doc.salary_structure}, 'salary_component', (r) => {
		var gross_pay = 0.0;
		$.each(frm.doc["earnings"], function(i, earning) {
			if (earning.salary_component == r.salary_component) {
				earning.amount = wages_amount;
				frm.refresh_fields('earnings');
			}
			gross_pay += earning.amount;
		});
		frm.set_value('gross_pay', gross_pay);

		frm.doc.net_pay = flt(frm.doc.gross_pay) - flt(frm.doc.total_deduction);
		frm.doc.rounded_total = Math.round(frm.doc.net_pay);
		refresh_many(['net_pay', 'rounded_total']);
	});
}

var calculate_totals = function(doc) {
	debugger;
	var tbl1 = doc.earnings || [];
	var tbl2 = doc.deductions || [];

	var total_earn = 0; var total_ded = 0;
	for(var i = 0; i < tbl1.length; i++){
		total_earn += flt(tbl1[i].amount);
	}
	for(var j = 0; j < tbl2.length; j++){
		total_ded += flt(tbl2[j].amount);
	}
	doc.gross_pay = total_earn;
	doc.total_deduction = total_ded;
	doc.net_pay = 0.0
	if(doc.salary_slip_based_on_timesheet == 0){
		doc.net_pay = flt(total_earn) - flt(total_ded) - flt(doc.total_loan_repayment);
		doc.rounded_total = Math.round(doc.net_pay)
	}
	refresh_many(['gross_pay', 'total_deduction', 'net_pay', 'rounded_total']);
}

cur_frm.cscript.validate = function(doc, cdt, cdn) {
	calculate_totals(doc);
}


frappe.ui.form.on('Salary Detail', {
	amount: function(frm) {
		calculate_totals(frm.doc);
	},

	earnings_remove: function(frm) {
		calculate_totals(frm.doc);
	},

	deductions_remove: function(frm) {
		calculate_totals(frm.doc);
	},

	salary_component: function(frm, cdt, cdn) {
		debugger;
		var child = locals[cdt][cdn];
		if(child.salary_component){
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Salary Component",
					name: child.salary_component
				},
				callback: function(data) {
					if(data.message){
						var result = data.message;
						frappe.model.set_value(cdt, cdn, 'condition', result.condition);
						frappe.model.set_value(cdt, cdn, 'amount_based_on_formula', result.amount_based_on_formula);
						if(result.amount_based_on_formula == 1){
							frappe.model.set_value(cdt, cdn, 'formula', result.formula);
						}
						else{
							frappe.model.set_value(cdt, cdn, 'amount', result.amount);
						}
						frappe.model.set_value(cdt, cdn, 'statistical_component', result.statistical_component);
						frappe.model.set_value(cdt, cdn, 'depends_on_payment_days', result.depends_on_payment_days);
						frappe.model.set_value(cdt, cdn, 'do_not_include_in_total', result.do_not_include_in_total);
						frappe.model.set_value(cdt, cdn, 'variable_based_on_taxable_salary', result.variable_based_on_taxable_salary);
						frappe.model.set_value(cdt, cdn, 'is_tax_applicable', result.is_tax_applicable);
						frappe.model.set_value(cdt, cdn, 'is_flexible_benefit', result.is_flexible_benefit);
						refresh_field("earnings");
						refresh_field("deductions");
					}
				}
			});
		}
	},

	amount_based_on_formula: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(child.amount_based_on_formula == 1){
			frappe.model.set_value(cdt, cdn, 'amount', null);
		}
		else{
			frappe.model.set_value(cdt, cdn, 'formula', null);
		}
	}
})
