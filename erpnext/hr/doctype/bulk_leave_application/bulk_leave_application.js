// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Leave Application', {
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

	refresh: function(frm) {
		frm.page.set_primary_action(__('Submit'), function() {
			if (!frm.doc.employee) {
				frappe.throw(__("Employee is mandatory"));
			} else if ((frm.doc.periods || []).length == 0) {
				frappe.throw(__("Please enter leave details in the child table"));
			} else {
				frappe.call({
					method: 'create_leave_applications',
					doc: frm.doc,
				}).then(r => {
					if(!r.exc) {
						frappe.msgprint(__("Leaves submitted for {0}", [frm.doc.employee]));

						$.each(["employee", "employee_name", "department", "branch"], function(i, field) {
							frm.set_value(field, "");
						});

						frm.clear_table("periods");
						refresh_field("periods");
					}
				});
			}
		});
	},

});

frappe.ui.form.on('Leave Application Period', {
	half_day: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.from_date == row.to_date) {
			frappe.model.set_value(cdt, cdn, "half_day_date", row.from_date);
		}
		calculate_total_days(frm, cdt, cdn);
	},

	from_date: function(frm, cdt, cdn) {
		calculate_total_days(frm, cdt, cdn);
	},

	to_date: function(frm, cdt, cdn) {
		calculate_total_days(frm, cdt, cdn);
	},

	half_day_date(frm, cdt, cdn) {
		calculate_total_days(frm, cdt, cdn);
	}
});

var calculate_total_days = function(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if(row.from_date && row.to_date && frm.doc.employee && row.leave_type) {

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
				"leave_type": row.leave_type,
				"from_date": row.from_date,
				"to_date": row.to_date,
				"half_day": row.half_day,
				"half_day_date": row.half_day_date,
			},
			callback: function(r) {
				if (r && r.message) {
					frappe.model.set_value(cdt, cdn, 'total_leave', r.message);
				}
			}
		});
	}
};