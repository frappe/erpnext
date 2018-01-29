// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/projects/timesheet_common.js' %};

frappe.ui.form.on('Timesheet Creation Tool', {
	onload: function(frm) {
		frm.set_value("company", '');
		frm.set_value("employees", []);
		frm.set_value("time_logs", []);
	},

	refresh: function(frm) {
		frm.disable_save();
	},

	create_timesheet: function(frm) {
		return frm.call({
			doc: frm.doc,
			freeze: true,
			method: "create_timesheet",
			freeze_message: __("Creating Timesheets"),
			callback: (r) => {	
				if(!r.exc){
					frappe.msgprint(__("Timesheets Created. " + `<a href= "#List/Timesheet" style='text-decoration: underline'>View Timesheets</a>`));
					frm.clear_table("employees");
					frm.clear_table("time_logs");
					frm.refresh_fields();
					frm.reload_doc();
				}
			}
		});
	},

	submit_timesheet: function(frm) {
		frappe.confirm(__("Permanently Submit Timesheet?"), () => {
			frm.call({
				doc: frm.doc,
				freeze: true,
				method: "submit_timesheet",
				freeze_message: __("Submitting Timesheets"),
				callback: (r) => {
					if(!r.exc){
						frappe.msgprint(__("Timesheets submitted. " + `<a href= "#List/Timesheet" style='text-decoration: underline'>View Timesheets</a>`));
						frm.clear_table("employees");
						frm.clear_table("time_logs");
						frm.refresh_fields();
						frm.reload_doc();
					}
				}
			});
		})
	},
});
