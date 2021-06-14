// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Overtime Slip', {
	onload: function (frm) {
		frm.set_query("employee", () => {
			return {
				query: "erpnext.controllers.queries.employee_query"
			};
		});
	},

	employee: function (frm) {
		if (frm.doc.employee) {
			frm.events.set_frequency_and_dates(frm).then(() => {
				frm.events.get_emp_details_and_overtime_duration(frm);
			});
		}
	},

	from_date: function (frm) {

		if (frm.doc.employee) {
			frm.events.set_frequency_and_dates(frm).then(() => {
				frm.events.get_emp_details_and_overtime_duration(frm);
			});
		}
	},

	set_frequency_and_dates: function (frm) {
		return frappe.call({
			method: "erpnext.payroll.doctype.overtime_slip.overtime_slip.get_frequency_and_dates",
			args: {
				employee: frm.doc.employee,
				date: frm.doc.from_date || frm.doc.posting_date,
			},
			callback: function (r) {
				frm.set_value("payroll_frequency", r.message[1]);
				if (r.message[0].start_date != frm.doc.from_date) {
					frm.set_value("from_date", r.message[0].start_date);
				}
				frm.set_value("to_date", r.message[0].end_date);
			}
		});
	},

	get_emp_details_and_overtime_duration: function (frm) {
		if (frm.doc.employee) {
			return frappe.call({
				method: 'get_emp_and_overtime_details',
				doc: frm.doc,
				callback: function () {
					frm.refresh();
				}
			});
		}
	},
});

frappe.ui.form.on('Overtime Details', {
	date: function (frm, cdt, cdn) {
		let child = locals[cdt][cdn];
		if (child.date) {
			frappe.call({
				method: "erpnext.payroll.doctype.overtime_slip.overtime_slip.get_standard_working_hours",
				args: {
					employee: frm.doc.employee,
					date: child.date,
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, 'standard_working_time', r.message);
					}
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, 'standard_working_time', 0);
		}
	}
});
