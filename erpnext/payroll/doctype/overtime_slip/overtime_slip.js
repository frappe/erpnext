// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Overtime Slip', {
	onload: function() {

	},
	employee: function(frm) {
		if (frm.doc.employee) {
			frm.events.set_frequency_and_dates(frm);
			frm.events.get_emp_details_and_overtime_duration(frm);
		}
	},


	from_date: function(frm) {
		if (frm.doc.employee) {
			frm.events.set_frequency_and_dates(frm);
			frm.events.get_emp_details_and_overtime_duration(frm);
		}
	},

	set_frequency_and_dates: function(frm) {
		frappe.call({
			method: "erpnext.payroll.doctype.overtime_slip.overtime_slip.get_frequency_and_dates",
			args: {
				employee: frm.doc.employee,
				date: frm.doc.from_date || frm.doc.posting_date,
			},
			callback: function(r) {
				frm.set_value("payroll_frequency", r.message[1]);
				frm.doc.from_date = r.message[0].start_date;
				frm.doc.to_date = r.message[0].end_date;
				frm.refresh();
			}
		});
	},

	get_emp_details_and_overtime_duration: function(frm) {
		if (frm.doc.employee) {
			return frappe.call({
				method: 'get_emp_and_overtime_details',
				doc: frm.doc,
				callback: function(r) {

				}
			});
		}
	},

	reset_value: function(frm) {

	}
});
