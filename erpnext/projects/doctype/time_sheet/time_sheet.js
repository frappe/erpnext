// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch("activity_type", "billing_rate", "billing_rate");

frappe.ui.form.on("Time Sheet", {
	setup: function(frm) {
		frm.get_field('timesheets').grid.editable_fields = [
			{fieldname: 'activity_type', columns: 2},
			{fieldname: 'from_time', columns: 2},
			{fieldname: 'hours', columns: 2},
			{fieldname: 'to_time', columns: 2},
		];

		frm.fields_dict.employee.get_query = function() {
			return {
				query:"erpnext.projects.doctype.time_sheet.time_sheet.get_employee_list"
			}
		}

		frm.fields_dict['timesheets'].grid.get_field('task').get_query = function(frm, cdt, cdn) {
			child = locals[cdt][cdn];
			return{
				filters: {
					'project': child.project
				}
			}
		}
	},

	onload: function(frm){
		if (frm.doc.__islocal && frm.doc.timesheets) {
			frm.set_value("employee", "")
			calculate_time_and_amount(frm);
		}
	},

	refresh: function(frm) {
		if(frm.doc.docstatus==1) {
			if(!frm.doc.sales_invoice && frm.doc.total_billing_amount > 0 
				&& frm.doc.employee){
				frm.add_custom_button(__("Make Sales Invoice"), function() { frm.trigger("make_invoice") },
					"icon-file-alt");
			}

			if(!frm.doc.salary_slip && frm.doc.employee){
				frm.add_custom_button(__("Make Salary Slip"), function() { frm.trigger("make_salary_slip") },
					"icon-file-alt");
			}
		}
	},

	make_invoice: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.time_sheet.time_sheet.make_sales_invoice",
			frm: frm
		});
	},

	make_salary_slip: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.time_sheet.time_sheet.make_salary_slip",
			frm: frm
		});
	},
})

frappe.ui.form.on("Time Sheet Detail", {
	timesheets_remove: function(frm) {
		calculate_time_and_amount(frm);
	},

	from_time: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn)
	},

	to_time: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if(frm._setting_hours) return;

		if(flt(child.hours) == 0.0){
			frappe.model.set_value(cdt, cdn, "hours", moment(child.to_time).diff(moment(child.from_time),
				"seconds") / 3600);
		}else{
			var d = moment(child.to_time);
			d.add(child.hours, "hours");
			frappe.model.set_value(cdt, cdn, "from_time", d.format(moment.defaultDatetimeFormat));
		}
	},

	hours: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn)
	},

	billing_rate: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn]
		if(child.hours && child.billing_rate){
			frappe.mode.set_value(cdt, cdn, 'total_billing_amount', flt(child.billing_rate * child.hours))
		}
		calculate_billing_amount(frm, cdt, cdn)
	},

	costing_rate: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn]
		frappe.mode.set_value(cdt, cdn, 'total_costing_amount', flt(child.costing_rate * child.hours))
		calculate_billing_amount(frm, cdt, cdn)
	},

	billable: function(frm, cdt, cdn) {
		calculate_billing_amount(frm, cdt, cdn)
	}
});

calculate_end_time = function(frm, cdt, cdn){
	var child = locals[cdt][cdn];

	if(!child.from_time) {
		frappe.model.set_value(cdt, cdn, "from_time", frappe.datetime.now_datetime());
	}

	var d = moment(child.from_time);
	d.add(child.hours, "hours");
	frm._setting_hours = true;
	frappe.model.set_value(cdt, cdn, "to_time", d.format(moment.defaultDatetimeFormat));
	frm._setting_hours = false;

	calculate_billing_amount(frm, cdt, cdn)
}

var calculate_billing_amount = function(frm, cdt, cdn){
	child = locals[cdt][cdn]
	billing_amount = 0.0

	if(child.hours && child.billable){
		billing_amount = (child.hours * child.billing_rate)	
	}

	frappe.model.set_value(cdt, cdn, 'billing_amount', billing_amount)
	calculate_time_and_amount(frm)
}

var calculate_time_and_amount = function(frm) {
	var tl = frm.doc.timesheets || [];
	total_hr = 0;
	total_billing_amount = 0;
	for(var i=0; i<tl.length; i++) {
		if (tl[i].hours) {
			total_hr += tl[i].hours;
			total_billing_amount += tl[i].billing_amount;
		}
	}

	cur_frm.set_value("total_hours", total_hr);
	cur_frm.set_value("total_billing_amount", total_billing_amount);
}