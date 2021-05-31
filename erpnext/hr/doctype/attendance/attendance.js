// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Attendance', {
	onload: function(frm) {

		frappe.db.get_single_value("Payroll Settings", "fetch_standard_working_hours_from_shift_type").then((r)=>{
			if (!r) {
				// for not fetching from Shift Type
				delete cur_frm.fetch_dict["shift"];
			}
		});

		if (frm.doc.__islocal) {
			cur_frm.set_value("attendance_date", frappe.datetime.get_today());
		}

		frm.set_query("employee", ()=>{
			return {
				query: "erpnext.controllers.queries.employee_query"
			};
		});
	},

	employee: function(frm) {
		if (frm.doc.employee) {
			frm.events.set_shift(frm);
			frm.events.set_overtime_type(frm);
		}
	},

	set_shift: function(frm) {
		frappe.call({
			method: "erpnext.hr.doctype.attendance.attendance.get_shift_type",
			args: {
				employee: frm.doc.employee,
				attendance_date: frm.doc.attendance_date
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value("shift", r.message);
				}
			}
		});
	},

	set_overtime_type: function(frm) {
		frappe.call({
			method: "erpnext.hr.doctype.attendance.attendance.get_overtime_type",
			args: {
				employee: frm.doc.employee,
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value("overtime_type", r.message);
				}
			}
		});
	},

	overtime_duration: function(frm) {
		let duration = frm.doc.overtime_duration.split(":");
		let overtime_duration_words = duration[0] + " Hours " + duration[1] + " Minutes";
		frm.set_value("overtime_duration_words",  overtime_duration_words);
	}

});
