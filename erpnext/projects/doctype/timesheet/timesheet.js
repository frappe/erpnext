// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');

frappe.ui.form.on("Timesheet", {
	setup: function(frm) {
		frm.fields_dict.employee.get_query = function() {
			return {
				filters:{
					'status': 'Active'
				}
			}
		}

		frm.fields_dict['time_logs'].grid.get_field('task').get_query = function(frm, cdt, cdn) {
			child = locals[cdt][cdn];
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
					"icon-file-alt");
			}

			if(!frm.doc.salary_slip && frm.doc.employee){
				frm.add_custom_button(__("Make Salary Slip"), function() { frm.trigger("make_salary_slip") },
					"icon-file-alt");
			}
		}

		if(frm.doc.per_billed > 0) {
			cur_frm.fields_dict["time_logs"].grid.toggle_enable("billing_hours", false);
			cur_frm.fields_dict["time_logs"].grid.toggle_enable("billable", false);
		}
		var me = this;
		setTimeout(function () {
			cur_frm.fields_dict["bar_code_no"].$input.keyup(function (frm) {
				frappe.call({
					method:"erpnext.projects.doctype.timesheet.timesheet.get_barcode",
					args:{
						fields: $(this).val()
					},
					callback: function (data) {
						if (data.message){
							set_values_on_barcode_change(data.message);
						}
					}
				})
			})
		},100);
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
	machine_no: function (frm) {
		frappe.call({
			method:'frappe.client.get',
			args:{
				doctype:"Machine",
				name: frm.doc.machine_no
			},
			callback:function (data) {
				if(data.message){
					cur_frm.set_value('machine_name',data.message.machine_name);
					cur_frm.set_value('gg',data.message.gg);
				}
			}
		});
	}
})

var set_values_on_barcode_change = function (doc) {
	var parentDoc = cur_frm.doc;
	cur_frm.set_value('machine_no',doc.machine_id);
	cur_frm.script_manager.trigger('refresh',parentDoc.doctype,parentDoc.name);
	cur_frm.set_value('production_order',doc.production_order);
	parentDoc.time_logs = [];
	var r = frappe.model.add_child(parentDoc,"Timesheet Detail","time_logs");
	r.operation_id = doc.operation;
	r.completed_qty = doc.qty;
	frappe.call({
		method:'frappe.client.get',
		args:{
			doctype:"Production Order Operation",
			name:r.operation_id
		},
		callback:function (data) {
			if (data.message) {
				frappe.model.set_value(r.doctype, r.name, "operation", data.message.operation);
			}
		}
	});
	cur_frm.refresh_field('time_logs');
	// console.log(r);
};

frappe.ui.form.on("Timesheet Detail", {
	time_logs_remove: function(frm) {
		calculate_time_and_amount(frm);
	},

	from_time: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn)
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
		child = locals[cdt][cdn];
		frappe.call({
			method: "erpnext.projects.doctype.timesheet.timesheet.get_activity_cost",
			args: {
				employee: frm.doc.employee,
				activity_type: child.activity_type
			},
			callback: function(r){
				if(r.message){
					frappe.model.set_value(cdt, cdn, 'billing_rate', r.message['billing_rate']);
					frappe.model.set_value(cdt, cdn, 'costing_rate', r.message['costing_rate']);
					calculate_billing_costing_amount(frm, cdt, cdn)
				}
			}
		})
	}
});

calculate_end_time = function(frm, cdt, cdn){
	var child = locals[cdt][cdn];

	var d = moment(child.from_time);
	d.add(child.hours, "hours");
	frm._setting_hours = true;
	frappe.model.set_value(cdt, cdn, "to_time", d.format(moment.defaultDatetimeFormat));
	frm._setting_hours = false;

	if(frm.doc.__islocal && !child.billing_hours && child.hours){
		frappe.model.set_value(cdt, cdn, "billing_hours", child.hours);
	}
}

var calculate_billing_costing_amount = function(frm, cdt, cdn){
	child = locals[cdt][cdn]
	billing_amount = costing_amount = 0.0;

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
	total_working_hr = 0;
	total_billing_hr = 0;
	total_billable_amount = 0;
	total_costing_amount = 0;
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

	cur_frm.set_value("total_billable_hours", total_billing_hr);
	cur_frm.set_value("total_hours", total_working_hr);
	cur_frm.set_value("total_billable_amount", total_billable_amount);
	cur_frm.set_value("total_costing_amount", total_costing_amount);
}
