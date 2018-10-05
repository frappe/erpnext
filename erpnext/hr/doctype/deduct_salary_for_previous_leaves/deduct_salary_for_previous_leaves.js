// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deduct Salary for Previous Leaves', {
	setup: function(frm) {
		frm.set_query("employee", function() {
			return {
				filters: {
					company: frm.doc.company,
					status: "Active"
				}
			};
		});
	}
});


frappe.ui.form.on('Previous Leave Period', {
	from_date: function(frm, cdt, cdn) {
		calculate_total_days(frm, cdt, cdn);
	},

	to_date: function(frm, cdt, cdn) {
		calculate_total_days(frm, cdt, cdn);
	},
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
				"to_date": row.to_date
			},
			callback: function(r) {
				if (r && r.message) {
					frappe.model.set_value(cdt, cdn, 'total_days', r.message);
				}
			}
		});
	}
};