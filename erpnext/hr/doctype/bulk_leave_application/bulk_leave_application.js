// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

var month_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

frappe.ui.form.on('Bulk Leave Application', {
	onload: function(frm) {
		// set default value for year and month
		if(frm.is_new()) {
			var today = new Date();
			frm.set_value("year", today.getFullYear());
			frm.set_value("month", month_list[today.getMonth()]);
		}
		if(frm.doc.docstatus == 0) {
			frm.fields_dict.leave_date.datepicker.update({ autoClose: false });
			frm.fields_dict.half_day_date.datepicker.update({ autoClose: false });	
		}
	},

	setup: function(frm) {
		frm.add_fetch("employee", "employee_name", "employee_name");
		frm.add_fetch("employee", "department", "department");
		frm.add_fetch("employee", "branch", "branch");

		frm.set_query("employee", function() {
			return {
				filters: {
					company: frm.doc.company,
					status: "Active"
				}
			};
		});
	},

	leave_date: function(frm) {
		frm.events.add_date_in_child_table(frm, frm.doc.leave_date);
	},

	half_day_date: function(frm) {
		frm.events.add_date_in_child_table(frm, frm.doc.half_day_date,
			frm.doc.half_day_date, frm.doc.half_day_date);
	},

	full_month_leave: function(frm) {
		if(frm.doc.full_month_leave) {
			var m = month_list.indexOf(frm.doc.month);
			var month_start_date = dateutil.obj_to_str(new Date(frm.doc.year, m, 1));
			var month_end_date = dateutil.obj_to_str(new Date(frm.doc.year, m + 1, 0));
			frm.events.add_date_in_child_table(frm, month_start_date, month_end_date);
		}
	},

	add_date_in_child_table: function(frm, from_date, to_date, half_day_date) {
		var row = frm.add_child("date_ranges");
		row.leave_type = frm.doc.leave_type;
		row.from_date = from_date;
		row.to_date = to_date || from_date;
		row.days = 1;
		if(half_day_date) {
			row.half_day = 1;
			row.half_day_date = half_day_date;
			row.days = 0.5;
		}
		refresh_field("date_ranges");
		calculate_total_days(frm);
	}
});

frappe.ui.form.on('Leave Application Period', {
	from_date: function(frm, cdt, cdn) {
		calculate_range_days(frm, cdt, cdn);
	},

	to_date: function(frm, cdt, cdn) {
		calculate_range_days(frm, cdt, cdn);
	}
});

var calculate_range_days = function(frm, cdt, cdn) {
	if(!frm.doc.employee) {
		frappe.throw(__("Employee is mandatory"));
	} else if(!frm.doc.leave_type) {
		frappe.throw(__("Leave Type is mandatory"));
	}
	var row = locals[cdt][cdn];
	if(row.from_date && row.to_date) {
		var from_date = Date.parse(row.from_date);
		var to_date = Date.parse(row.to_date);

		if(to_date < from_date){
			frappe.msgprint(__("To Date cannot be less than From Date"));
			frappe.model.set_value(cdt, cdn, 'to_date', '');
			return;
		}

		// server call is done to include holidays in leave days calculations
		return frappe.call({
			method: 'erpnext.hr.doctype.leave_application.leave_application.get_number_of_leave_days',
			args: {
				"employee": frm.doc.employee,
				"leave_type": frm.doc.leave_type,
				"from_date": row.from_date,
				"to_date": row.to_date,
			},
			callback: function(r) {
				if (r && r.message) {
					frappe.model.set_value(cdt, cdn, 'days', r.message);
					calculate_total_days(frm);
				}
			}
		});
	}
};

var calculate_total_days = function(frm) {
	var range_days = 0;
	$.each(frm.doc.date_ranges || [], function(i, row) {
		range_days += flt(row.days);
	})

	frm.set_value("total_leaves", range_days);
};