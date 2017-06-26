// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Timesheet", {
	setup: function(frm) {
		frm.add_fetch('employee', 'employee_name', 'employee_name');
		frm.fields_dict.employee.get_query = function() {
			return {
				filters:{
					'status': 'Active'
				}
			}
		}

		frm.fields_dict['time_logs'].grid.get_field('task').get_query = function(frm, cdt, cdn) {
			var child = locals[cdt][cdn];
			return{
				filters: {
					'project': child.project,
					'status': ["!=", "Closed"]
				}
			}
		}

		frm.fields_dict['time_logs'].grid.get_field('project').get_query = function() {
			return{
				filters: {
					'company': frm.doc.company
				}
			}
		}
	},

	onload: function(frm){
		if (frm.doc.__islocal && frm.doc.time_logs) {
			calculate_time_and_amount(frm);
		}
	},

	refresh: function(frm) {
		if(frm.doc.docstatus==1) {
			if(frm.doc.per_billed < 100){
				frm.add_custom_button(__("Make Sales Invoice"), function() { frm.trigger("make_invoice") },
					"fa fa-file-alt");
			}

			if(!frm.doc.salary_slip && frm.doc.employee){
				frm.add_custom_button(__("Make Salary Slip"), function() { frm.trigger("make_salary_slip") },
					"fa fa-file-alt");
			}
		}

		if(frm.doc.per_billed > 0) {
			frm.fields_dict["time_logs"].grid.toggle_enable("billing_hours", false);
			frm.fields_dict["time_logs"].grid.toggle_enable("billable", false);
		}
	},

	make_invoice: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.timesheet.timesheet.make_sales_invoice",
			frm: frm
		});
	},

	make_salary_slip: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.timesheet.timesheet.make_salary_slip",
			frm: frm
		});
	},
})

frappe.ui.form.on("Timesheet Detail", {
	time_logs_remove: function(frm) {
		calculate_time_and_amount(frm);
	},

	from_time: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn);
	},

	to_time: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if(frm._setting_hours) return;
		frappe.model.set_value(cdt, cdn, "hours", moment(child.to_time).diff(moment(child.from_time),
			"seconds") / 3600);
	},

	hours: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn)
	},

	billing_hours: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	billing_rate: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	costing_rate: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	billable: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	activity_type: function(frm, cdt, cdn) {
		frm.script_manager.copy_from_first_row('time_logs', frm.selected_doc,
			'project');

		frappe.call({
			method: "erpnext.projects.doctype.timesheet.timesheet.get_activity_cost",
			args: {
				employee: frm.doc.employee,
				activity_type: frm.selected_doc.activity_type
			},
			callback: function(r){
				if(r.message){
					frappe.model.set_value(cdt, cdn, 'billing_rate', r.message['billing_rate']);
					frappe.model.set_value(cdt, cdn, 'costing_rate', r.message['costing_rate']);
					calculate_billing_costing_amount(frm, cdt, cdn);
				}
			}
		})
	}
});

var calculate_end_time = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];

	var d = moment(child.from_time);
	d.add(child.hours, "hours");
	frm._setting_hours = true;
	frappe.model.set_value(cdt, cdn, "to_time", d.format(moment.defaultDatetimeFormat));
	frm._setting_hours = false;

	if((frm.doc.__islocal || frm.doc.__onload.maintain_bill_work_hours_same) && child.hours){
		frappe.model.set_value(cdt, cdn, "billing_hours", child.hours);
	}
}

var calculate_billing_costing_amount = function(frm, cdt, cdn){
	var child = locals[cdt][cdn]
	var billing_amount = 0.0;
	var costing_amount = 0.0;

	if(child.billing_hours && child.billable){
		billing_amount = (child.billing_hours * child.billing_rate);
		costing_amount = flt(child.costing_rate * child.billing_hours);
	}

	frappe.model.set_value(cdt, cdn, 'billing_amount', billing_amount);
	frappe.model.set_value(cdt, cdn, 'costing_amount', costing_amount);
	calculate_time_and_amount(frm)
}

var calculate_time_and_amount = function(frm) {
	var tl = frm.doc.time_logs || [];
	var total_working_hr = 0;
	var total_billing_hr = 0;
	var total_billable_amount = 0;
	var total_costing_amount = 0;
	for(var i=0; i<tl.length; i++) {
		if (tl[i].hours) {
			total_working_hr += tl[i].hours;
			total_billable_amount += tl[i].billing_amount;
			total_costing_amount += tl[i].costing_amount;

			if(tl[i].billable){
				total_billing_hr += tl[i].billing_hours;
			}
		}
	}

	frm.set_value("total_billable_hours", total_billing_hr);
	frm.set_value("total_hours", total_working_hr);
	frm.set_value("total_billable_amount", total_billable_amount);
	frm.set_value("total_costing_amount", total_costing_amount);
}